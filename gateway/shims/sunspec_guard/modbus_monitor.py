import time, csv, math
from datetime import datetime
from pathlib import Path
from pymodbus.client.sync import ModbusTcpClient

HOST, PORT, UNIT = "127.0.0.1", 5020, 1
OUT = Path("data/processed/modbus_tap.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

def read9(client):
    rr = client.read_holding_registers(address=0, count=9, unit=UNIT)
    if rr.isError(): return None
    r = rr.registers
    return dict(
        V1_V=r[0]/1.0, V1_pu=r[1]/1000.0, f_Hz=r[2]/100.0,
        P_PV_kW=r[3]/10.0, Q_PV_kVAR=r[4]/10.0,
        P_Source_kW=r[5]/10.0, Q_Source_kVAR=r[6]/10.0,
        pf_src=r[7]/1000.0, pf_pv=r[8]/1000.0,
    )

def main():
    client = ModbusTcpClient(HOST, port=PORT)
    assert client.connect(), "Cannot connect to Modbus server"

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        header = ["timestamp","V1_V","V1_pu","f_Hz","P_PV_kW","Q_PV_kVAR",
                  "P_Source_kW","Q_Source_kVAR","pf_src","pf_pv"]
        w.writerow(header)

        prev = None
        while True:
            now = datetime.now().isoformat()
            vals = read9(client)
            if not vals:
                print("❌ read error"); time.sleep(1); continue

            row = [now] + [vals[k] for k in header[1:]]
            w.writerow(row); f.flush()

            # Very simple anomaly rules
            alerts = []
            if not (0.90 <= vals["V1_pu"] <= 1.10): alerts.append("Vpu_out_of_range")
            if not (59.5 <= vals["f_Hz"] <= 60.5): alerts.append("freq_out_of_range")
            if prev:
                if abs(vals["P_PV_kW"] - prev["P_PV_kW"]) > 100: alerts.append("Ppv_ramp_impossible")
                if abs(vals["P_Source_kW"] - prev["P_Source_kW"]) > 200: alerts.append("Psrc_ramp_impossible")
            if alerts:
                print(f"[ALERT] {now} -> {', '.join(alerts)}")

            prev = vals
            time.sleep(1.0)

if __name__ == "__main__":
    main()
