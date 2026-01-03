#!/usr/bin/env python3
"""Simple DI check script: reads Modbus discrete inputs and prints interpreted status using di_config."""
import os
import sys

# Ensure project root is on sys.path so imports work when script is run from scripts/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from pymodbus.client.sync import ModbusTcpClient
except Exception:
    try:
        from pymodbus.client import ModbusTcpClient
    except Exception:
        print('Failed to import ModbusTcpClient from pymodbus')
        raise

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
    # Support different pymodbus signatures (unit / slave / no unit)
    r = None
    for kwargs in ({'unit': UNIT}, {'slave': UNIT}, {}):
        try:
            r = c.read_discrete_inputs(0, DI_COUNT, **kwargs)
            break
        except TypeError:
            continue

    if not r:
        print('Modbus read failed (no response)')
        c.close()
        return 2

    # r may expose 'bits' or be a list/iterable
    if hasattr(r, 'bits'):
        bits = list(map(int, r.bits[:DI_COUNT]))
    else:
        try:
            bits = list(map(int, list(r)[:DI_COUNT]))
        except Exception:
            print('Unexpected Modbus response:', r)
            c.close()
            return 3
    for idx, bit in enumerate(bits):
        info = get_di_info(idx)
        status = get_status_text(idx, bit)
        ok = is_di_ok(idx, bit)
        print(f"DI{idx+1:02d}: {info['name']:<25} raw={bit} -> {status}  (OK={ok})")

    c.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
