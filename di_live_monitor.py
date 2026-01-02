#!/usr/bin/env python3
"""
Live DI Monitor - Realtidsövervakning av digitala ingångar
Uppdateras varje sekund för snabb feedback under tester

ARKITEKTUR:
- Modbus läser GPIO RAW (ingen invertering)
- di_config.py definierar vad HIGH/LOW betyder
- Denna monitor visar både RAW och logisk tolkning
"""
import time
import sys
from pymodbus.client import ModbusTcpClient
from datetime import datetime
from di_config import get_di_info, get_status_text

def clear_screen():
    """Rensar skärmen"""
    print("\033[2J\033[H", end='')

def read_di_status(client):
    """Läs alla DI-status från Modbus"""
    try:
        result = client.read_discrete_inputs(0, 12, slave=1)
        if result.isError():
            return None
        return result.bits[:12]
    except Exception as e:
        return None

def print_status(bits):
    """Skriv ut DI-status med både RAW och logisk tolkning"""
    clear_screen()
    print('=' * 100)
    print(f'  📊 LIVE DI MONITOR - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 100)
    print()
    print('  🔄 Uppdateras varje sekund. Tryck Ctrl+C för att avsluta.')
    print('  📖 RAW GPIO-läsning. Applikationslogik tolkar vad HIGH/LOW betyder.\n')
    print('=' * 100)
    
    for i, state in enumerate(bits):
        config = get_di_info(i)
        num = i + 1
        
        # Visa RAW GPIO-värde
        gpio_display = '🟢 HIGH (1)' if state else '🔴 LOW  (0)'
        
        # Visa logisk tolkning
        status = get_status_text(i, state)
        
        # Visa typ och vad HIGH betyder
        type_info = f"[{config['type']}: HIGH={config['high_means']}]"
        critical_marker = ' 🔴 KRITISK' if config.get('critical') else ''
        
        line = f"  DI{num:2d} {gpio_display} {status:12s} - {config['name']}{critical_marker} {type_info}"
        
        if config.get('note'):
            line += f"\n       └─ {config['note']}"
        
        print(line)
    
    print('=' * 100)

def main():
    client = ModbusTcpClient('127.0.0.1', port=502, timeout=3)
    
    if not client.connect():
        print('❌ Kunde inte ansluta till Modbus på 127.0.0.1:502')
        print('   Kontrollera att unipi-modbus.service körs:')
        print('   sudo systemctl status unipi-modbus.service')
        sys.exit(1)
    
    try:
        print('\n🚀 Startar live monitoring...\n')
        time.sleep(1)
        
        while True:
            bits = read_di_status(client)
            if bits is None:
                clear_screen()
                print('❌ Fel vid läsning av DI-status')
                time.sleep(5)
                continue
            
            print_status(bits)
            time.sleep(1)
            
    except KeyboardInterrupt:
        clear_screen()
        print('\n✅ Live monitoring avslutad\n')
    finally:
        client.close()

if __name__ == '__main__':
    main()
