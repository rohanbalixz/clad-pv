import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import opendssdirect as dss

# ---- Config ----
START = datetime(2025, 8, 10, 6, 0, 0)  # start 06:00
NPTS = 96                                # 15-min resolution for one day
STEP_MIN = 15
OUT_DIR = Path("data/raw/telemetry")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "opendss_pv_day1_15min.csv"

# ---- Build irradiance profile (0..1), bell curve peaking ~13:00 ----
t = np.arange(NPTS)
noon_idx = (13 - 6) * 4  # 13:00 relative to 06:00 baseline (15-min steps)
width = 5 * 4            # ~5 hours spread
irr = np.exp(-0.5 * ((t - noon_idx) / width) ** 2)
# zero outside 06:00–20:00 already implicit by NPTS window; clamp tiny tails
irr[irr < 1e-3] = 0.0

# ---- OpenDSS model ----
dss.Basic.ClearAll()
dss.Text.Command("New Circuit.PVFeed basekv=12.47 pu=1.0 phases=3 bus1=sourcebus")
dss.Text.Command("Edit Vsource.Source phases=3 bus1=sourcebus basekv=12.47 pu=1.0")

# Simple line from source to pv/load bus
dss.Text.Command("New Linecode.Feeder r1=0.2 x1=0.4 r0=0.4 x0=0.8 units=km")
dss.Text.Command("New Line.Lsrc phases=3 bus1=sourcebus bus2=pvbus length=1 units=km linecode=Feeder")

# 200 kW daytime load at pvbus (approx PF 0.98)
dss.Text.Command("New Load.L1 phases=3 bus1=pvbus kv=12.47 kw=200 pf=0.98")

# PV system at pvbus (nameplate 300 kW AC, will be scaled by irradiance)
# Use 'daily' shape for irradiance
mults = ",".join(f"{x:.5f}" for x in irr)
dss.Text.Command(f"New Loadshape.Irrad npts={NPTS} interval={STEP_MIN} mult=({mults})")
dss.Text.Command("New PVSystem.PV phases=3 bus1=pvbus kv=12.47 kva=330 pmpp=300 pf=1.0 daily=Irrad")

# Enable dynamics: use Daily mode stepping manually to capture each point
dss.Text.Command("Set mode=daily stepsize=15m")

rows = []
current_time = START

for i in range(NPTS):
    # Solve one step
    dss.Text.Command("Solve number=1")

    # Active bus voltage magnitudes (L-N) at pvbus
    dss.Circuit.SetActiveBus("pvbus")
    vmags = dss.Bus.VMagAngle()[0::2]  # [Vmag1, ang1, Vmag2, ang2, ...] -> take mags

    # PV P/Q: sum real/reactive across terminals
    dss.Circuit.SetActiveElement("PVSystem.PV")
    pvsys_powers = dss.CktElement.Powers()  # P1, Q1, P2, Q2, ...
    P_pv = sum(pvsys_powers[0::2])   # sum of P across phases
    Q_pv = sum(pvsys_powers[1::2])   # sum of Q across phases

    # Load P/Q at L1
    dss.Circuit.SetActiveElement("Load.L1")
    load_powers = dss.CktElement.Powers()
    P_load = sum(load_powers[0::2])
    Q_load = sum(load_powers[1::2])

    # Source total P/Q and frequency
    P_total = dss.Circuit.TotalPower()  # returns [P_MW, Q_MVAR]
    P_src_MW, Q_src_MVAR = P_total[0], P_total[1]
    f_hz = dss.Solution.Frequency()

    rows.append({
        "timestamp": current_time,
        "irradiance_norm": irr[i],
        "V1_V": round(vmags[0], 2) if len(vmags) > 0 else None,
        "V2_V": round(vmags[1], 2) if len(vmags) > 1 else None,
        "V3_V": round(vmags[2], 2) if len(vmags) > 2 else None,
        "P_PV_kW": round(P_pv, 3),
        "Q_PV_kVAR": round(Q_pv, 3),
        "P_Load_kW": round(P_load, 3),
        "Q_Load_kVAR": round(Q_load, 3),
        "P_Source_kW": round(P_src_MW * 1000.0, 3),
        "Q_Source_kVAR": round(Q_src_MVAR * 1000.0, 3),
        "f_Hz": round(f_hz, 4),
    })

    current_time += timedelta(minutes=STEP_MIN)

df = pd.DataFrame(rows)
df.to_csv(OUT_FILE, index=False)
print(f"Wrote OpenDSS PV telemetry: {OUT_FILE} ({len(df)} rows)")
