#!/usr/bin/env python3
"""Simple DI check script: reads Modbus discrete inputs and prints interpreted status using di_config."""
from pymodbus.client.sync import ModbusTcpClient
from di_config import get_di_info, get_status_text, is_di_ok

MODBUS_HOST = '127.0.0.1'
MODBUS_PORT = 502
UNIT = 1
DI_COUNT = 12


def main():
    c = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
    if not c.connect():
        print('Modbus connect failed')
        return 1
    r = c.read_discrete_inputs(0, DI_COUNT, unit=UNIT)
    if not r or not hasattr(r, 'bits'):
        print('Modbus read failed:', r)
        c.close()
        return 2

    bits = list(map(int, r.bits[:DI_COUNT]))
    for idx, bit in enumerate(bits):
        info = get_di_info(idx)
        status = get_status_text(idx, bit)
        ok = is_di_ok(idx, bit)
        print(f"DI{idx+1:02d}: {info['name']:<25} raw={bit} -> {status}  (OK={ok})")

    c.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
