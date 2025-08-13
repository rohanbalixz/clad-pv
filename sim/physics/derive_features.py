import pandas as pd
from pathlib import Path
import numpy as np

in_file = Path("data/raw/telemetry/opendss_pv_day1_15min.csv")
out_dir = Path("data/processed")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "physics_features_day1.csv"

df = pd.read_csv(in_file, parse_dates=["timestamp"])

# Compute net injections at the source (positive = import from grid)
df["P_net_kW"] = df["P_Source_kW"]
df["Q_net_kVAR"] = df["Q_Source_kVAR"]

# Approximate per-unit voltage using phase A if present (base 7.2 kV L-N for 12.47kV L-L)
base_V_LN = 12470 / np.sqrt(3) / 2  # ~ 3600V? We'll use a simpler assumption: 12.47kV L-L => 7.2kV L-N
base_V_LN = 7200.0
df["V1_pu"] = df["V1_V"] / base_V_LN

# Power factor estimate for PV and source
def pf(p, q):
    s = np.sqrt(p**2 + q**2) + 1e-9
    return np.clip(p / s, -1.0, 1.0)

df["pf_pv"] = pf(df["P_PV_kW"], df["Q_PV_kVAR"])
df["pf_src"] = pf(df["P_Source_kW"], df["Q_Source_kVAR"])

# Simple finite-difference ramp features (rate of change)
df = df.sort_values("timestamp").reset_index(drop=True)
for col in ["P_PV_kW", "Q_PV_kVAR", "V1_pu", "P_Source_kW", "Q_Source_kVAR"]:
    df[f"d_{col}"] = df[col].diff()

# Keep tidy subset
keep = [
    "timestamp",
    "irradiance_norm",
    "V1_V", "V1_pu",
    "P_PV_kW", "Q_PV_kVAR", "pf_pv",
    "P_Load_kW", "Q_Load_kVAR",
    "P_Source_kW", "Q_Source_kVAR", "pf_src",
    "P_net_kW", "Q_net_kVAR",
    "d_P_PV_kW", "d_Q_PV_kVAR", "d_V1_pu", "d_P_Source_kW", "d_Q_Source_kVAR",
    "f_Hz"
]
df[keep].to_csv(out_file, index=False)
print(f"✅ Wrote features: {out_file} ({len(df)} rows)")
