# CLAD-PV: Cross-Layer Active Defense for Grid-Tied Solar Inverters

## Overview
End-to-end, Mac-native CPS security project that simulates grid-tied solar inverter behavior, emulates SunSpec/Modbus control, generates normal/attack traffic, and evaluates a physics-guided IDS with a lightweight authenticated shim.

## Repo Structure
- sim/: power & network simulation stubs
- gateway/: SunSpec-Guard (auth shim) + TinyML IDS
- models/: training & evaluation
- data/: raw/processed telemetry & pcaps (gitignored)
- notebooks/: EDA and experiments
- docs/: writeups, diagrams

## Getting Started
1) `python3 -m venv .venv && source .venv/bin/activate`
2) `pip install -r requirements.txt` (we'll add this next)
3) Run simulation, generate telemetry, train IDS.

## Milestones
- Stage-1: Architecture, STRIDE+DREAD, gap analysis
- Stage-2: Prototype PG-IDS + SunSpec-Guard, dataset, eval
- Stage-3: Report + slides

## Notes
- Mac-only path uses OpenDSSDirect.py (no Windows required).
- PCAP parsing via pyshark (tshark recommended).
