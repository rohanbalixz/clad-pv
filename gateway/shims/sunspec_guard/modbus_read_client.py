from pymodbus.client.sync import ModbusTcpClient

HOST, PORT = "127.0.0.1", 5020
UNIT_ID = 1

def u16_to_val(x): return int(x) if isinstance(x, int) else 0

def main():
    client = ModbusTcpClient(HOST, port=PORT)
    if not client.connect():
        print("❌ Could not connect")
        return

    rr = client.read_holding_registers(address=0, count=9, unit=UNIT_ID)
    if rr.isError():
        print("❌ Read error:", rr)
        client.close()
        return

    regs = rr.registers
    V1_V         = u16_to_val(regs[0]) / 1.0
    V1_pu        = u16_to_val(regs[1]) / 1000.0
    f_Hz         = u16_to_val(regs[2]) / 100.0
    P_PV_kW      = u16_to_val(regs[3]) / 10.0
    Q_PV_kVAR    = u16_to_val(regs[4]) / 10.0
    P_Source_kW  = u16_to_val(regs[5]) / 10.0
    Q_Source_kVAR= u16_to_val(regs[6]) / 10.0
    pf_src       = u16_to_val(regs[7]) / 1000.0
    pf_pv        = u16_to_val(regs[8]) / 1000.0

    print("✅ Read OK")
    print(f"V1_V={V1_V:.1f}  V1_pu={V1_pu:.3f}  f_Hz={f_Hz:.2f}")
    print(f"P_PV={P_PV_kW:.1f} kW  Q_PV={Q_PV_kVAR:.1f} kVAR")
    print(f"P_Source={P_Source_kW:.1f} kW  Q_Source={Q_Source_kVAR:.1f} kVAR")
    print(f"pf_src={pf_src:.3f}  pf_pv={pf_pv:.3f}")

    client.close()

if __name__ == "__main__":
    main()
