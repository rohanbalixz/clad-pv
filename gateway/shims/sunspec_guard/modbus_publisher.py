import time
import math
import threading
import json
import pandas as pd
from pathlib import Path

from pymodbus.server.sync import StartTcpServer   # pymodbus v2.x
from pymodbus.datastore import (
    ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus import __version__ as pymodbus_ver

CSV = Path("data/processed/physics_features_day1.csv")
CONTROL = Path("gateway/shims/sunspec_guard/control.json")
PORT = 5020
UNIT_ID = 1

# ---- Read-only data block ----
class ReadOnlyDataBlock(ModbusSequentialDataBlock):
    """Ignore all write attempts (server becomes read-only to Modbus clients)."""
    def setValues(self, address, values):
        # Drop write attempts silently
        return

def scale(val, mul, clamp_low=0, clamp_high=65535):
    try:
        x = int(round(float(val) * mul))
        return max(clamp_low, min(clamp_high, x))
    except Exception:
        return 0

def read_control():
    """Read authenticated control inputs (e.g., curtailment) written by our secure API."""
    try:
        if CONTROL.exists():
            with CONTROL.open() as f:
                obj = json.load(f)
            c = obj.get("curtailment", 0.0)
            c = float(c)
            if not (0.0 <= c <= 1.0):
                return 0.0
            return c
    except Exception:
        pass
    return 0.0

def publisher_loop(ctx: ModbusServerContext, df: pd.DataFrame, period_sec: float = 1.0):
    i = 0
    n = len(df)
    while True:
        row = df.iloc[i % n]
        curtail = read_control()  # 0..1 fraction to reduce PV active power

        # Apply curtailment to P_PV (reduce active power)
        p_pv = float(row.get("P_PV_kW", 0.0))
        p_pv_curtailed = max(0.0, p_pv * (1.0 - curtail))

        registers = [
            scale(row.get("V1_V", 0), 1),            # 0:  V1_V * 1
            scale(row.get("V1_pu", 0), 1000),        # 1:  V1_pu * 1000
            scale(row.get("f_Hz", 60), 100),         # 2:  f_Hz * 100
            scale(p_pv_curtailed, 10),               # 3:  P_PV_kW * 10 (curtailed)
            scale(row.get("Q_PV_kVAR", 0), 10),      # 4:  Q_PV_kVAR * 10
            scale(row.get("P_Source_kW", 0), 10),    # 5:  P_Source_kW * 10
            scale(row.get("Q_Source_kVAR", 0), 10),  # 6:  Q_Source_kVAR * 10
            scale(row.get("pf_src", 1.0), 1000),     # 7:  pf_src * 1000
            scale(row.get("pf_pv", 1.0), 1000),      # 8:  pf_pv * 1000
        ]

        # Write to holding registers (block=3), starting at 0
        context = ctx[0]
        context.setValues(3, 0, registers)

        # Heartbeat in input registers (block=4) at addr 0
        hb = [(i % 10000)]
        context.setValues(4, 0, hb)

        if i % 10 == 0:
            print(f"[publisher] idx={i % n} curtail={curtail:.2f} V={registers[0]} f={registers[2]} Ppv={registers[3]}")

        i += 1
        time.sleep(period_sec)

def main():
    if not CSV.exists():
        raise SystemExit(f"CSV not found: {CSV}")

    df = pd.read_csv(CSV, parse_dates=["timestamp"])

    store = ModbusSlaveContext(
        di=ReadOnlyDataBlock(0, [0]*100),
        co=ReadOnlyDataBlock(0, [0]*100),
        hr=ReadOnlyDataBlock(0, [0]*100),   # holding registers read-only
        ir=ReadOnlyDataBlock(0, [0]*100),
        zero_mode=True,
    )
    context = ModbusServerContext(slaves=store, single=True)

    identity = ModbusDeviceIdentification()
    identity.VendorName = "CLAD-PV"
    identity.ProductCode = "PV"
    identity.VendorUrl = "http://localhost"
    identity.ProductName = "CLAD-PV Modbus Emulator"
    identity.ModelName = "PV-EMU-1"
    identity.MajorMinorRevision = pymodbus_ver

    t = threading.Thread(target=publisher_loop, args=(context, df, 1.0), daemon=True)
    t.start()

    print(f"✅ Starting Modbus/TCP server on 0.0.0.0:{PORT}, unit id {UNIT_ID}")
    print("   Holding registers 40001.. carry PV metrics (scaled). Writes are ignored (read-only).")
    StartTcpServer(context, identity=identity, address=("0.0.0.0", PORT))

if __name__ == "__main__":
    main()
