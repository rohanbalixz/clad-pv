import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# --- Config ---
minutes = 24 * 60  # 1 day at 1-min resolution
start = datetime(2025, 8, 10, 6, 0, 0)  # start at 06:00 local
dt = pd.date_range(start, periods=minutes, freq="T")
out_dir = Path("data/raw/telemetry")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "baseline_day1.csv"

# --- PV/Irradiance model (very simple) ---
# Solar irradiance: smooth bell shape peaking at solar noon (~ 13:00), zero at night
t = np.arange(minutes)
noon_idx = 13 * 60  # 13:00
width = 5 * 60      # ~5 hours spread
irradiance = np.exp(-0.5 * ((t - noon_idx) / width) ** 2)  # 0..1
irradiance[t < 6*60] = 0.0
irradiance[t > 20*60] = 0.0

# Ambient temp (°C): cool morning, warmer afternoon
tempC = 18 + 8 * np.exp(-0.5 * ((t - (15*60)) / (3*60)) ** 2)  # peaks ~15:00

# --- Inverter/PQ model ---
# Nameplate 50 kW PV, simple DC→AC with efficiency and PF control near unity
p_rated_kw = 50.0
eff = 0.97
p_kw = p_rated_kw * irradiance * eff

# Reactive power policy: mostly unity PF with small Q for voltage support
# Slight Q injection/absorption proportional to (1.0 - Vpu)
v_pu_base = 1.00 + 0.01 * np.sin(2 * np.pi * t / (24*60))  # daily slight drift
q_kvar = 0.05 * p_kw * (1.0 - v_pu_base) * 10  # bounded small Q support

# Power factor and derived signals
va = np.sqrt(np.maximum(p_kw**2 + q_kvar**2, 1e-9))
pf = np.clip(p_kw / va, 0.95, 1.0)

# Frequency near 60 Hz with slight random walk
rng = np.random.default_rng(42)
f_hz = 60.0 + 0.01 * np.cumsum(rng.normal(0, 0.001, size=minutes))

# THD% low at baseline with tiny noise
thd_pct = np.clip(1.5 + rng.normal(0, 0.1, size=minutes), 0.5, 3.0)

# Small measurement noise on voltage
v_pu = v_pu_base + rng.normal(0, 0.002, size=minutes)

# DataFrame
df = pd.DataFrame({
    "timestamp": dt,
    "irradiance_norm": irradiance,
    "tempC": np.round(tempC, 2),
    "P_kW": np.round(p_kw, 3),
    "Q_kVAR": np.round(q_kvar, 3),
    "V_pu": np.round(v_pu, 4),
    "f_Hz": np.round(f_hz, 4),
    "pf": np.round(pf, 4),
    "THD_pct": np.round(thd_pct, 3),
})

df.to_csv(out_file, index=False)
print(f"✅ Wrote baseline telemetry: {out_file} ({len(df)} rows)")
