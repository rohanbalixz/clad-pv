import opendssdirect as dss

print("OpenDSS version:", dss.Basic.Version())
dss.Basic.ClearAll()

# Circuit + source (OpenDSS auto-creates Vsource.Source when Circuit.* is created)
dss.Text.Command("New Circuit.Smoke basekv=12.47 pu=1.0 phases=3 bus1=sourcebus")
dss.Text.Command("Edit Vsource.Source phases=3 bus1=sourcebus basekv=12.47 pu=1.0")

# Line and load
dss.Text.Command("New Linecode.LC1 r1=0.2 x1=0.4 r0=0.4 x0=0.8 units=km")
dss.Text.Command("New Line.L1 phases=3 bus1=sourcebus bus2=loadbus length=0.5 units=km linecode=LC1")
dss.Text.Command("New Load.LD1 phases=3 bus1=loadbus kv=12.47 kw=300 pf=0.98")

# Solve a single powerflow
dss.Text.Command("Solve")

# Read voltage magnitudes on load bus
dss.Circuit.SetActiveBus("loadbus")
vmags = dss.Bus.VMagAngle()[0::2]  # mag,angle,... → take magnitudes
print("Load bus phase voltages (V):", [round(v,1) for v in vmags])
