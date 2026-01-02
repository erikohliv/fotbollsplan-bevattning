#!/usr/bin/env python3
"""
Digital Input Monitor - Real-time DI status
Visar live-status på alla digitala ingångar (DI1-DI12)
"""
import time
import sys
from pymodbus.client import ModbusTcpClient
from datetime import datetime

DI_LABELS = {
    0:  "DI1  - Lägesväljare AUTO (NC)",
    1:  "DI2  - Lägesväljare FJÄRR (NC)",
    2:  "DI3  - Nödstopp (NC) ⚠️ KRITISK",
    3:  "DI4  - Zonväljare Zon 1 (NO)",
    4:  "DI5  - Zonväljare Zon 2 (NO)",
    5:  "DI6  - Zonväljare Zon 3 (NO)",
    6:  "DI7  - Flödesvakt (NO)",
    7:  "DI8  - Mjukstartare fel (NC)",
    8:  "DI9  - Tryckvakt (NO)",
    9:  "DI10 - Motorskydd (NC) ⚠️ KRITISK",
    10: "I11  - 24VDC säkring (NO) ⚠️ KRITISK",
    11: "I12  - 24VAC säkring (NO) [EJ ANSLUTEN]"
}

def read_all_di(client):
    """Läs alla 12 digitala ingångar"""
    try:
        result = client.read_discrete_inputs(0, 12, slave=1)
        if result.isError():
            return None
        return result.bits[:12]
    except Exception as e:
        return None

def print_header():
    """Skriv ut header"""
    print("\n" + "="*80)
    print("DIGITAL INPUT MONITOR - LIVE STATUS")
    print("="*80)
    print("\n📍 INSTRUKTIONER:")
    print("   NC (Normally Closed)  = Förväntat HIGH (1) när OK, LOW (0) vid larm")
    print("   NO (Normally Open)    = Förväntat LOW (0) när inaktiv, HIGH (1) vid aktivering")
    print("\n   Trigga en ingång åt gången och se att status ändras nedan.")
    print("   Tryck Ctrl+C för att avsluta.\n")
    print("="*80)

def print_status_table(bits, last_bits):
    """Skriv ut status-tabell"""
    print("\n" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("-" * 80)
    
    for i in range(12):
        label = DI_LABELS[i]
        current = bits[i] if bits else False
        status = "HIGH (1)" if current else "LOW (0) "
        
        # Färgindikator
        if current:
            indicator = "🟢"  # Grön = HIGH
        else:
            indicator = "⚫"  # Svart = LOW
        
        # Highlight om status ändrats
        changed = ""
        if last_bits is not None and bits[i] != last_bits[i]:
            changed = " ← ÄNDRAD!"
            indicator = "🔴"  # Röd vid ändring
        
        print(f"  {indicator} {label}: {status}{changed}")
    
    print("-" * 80)

def main():
    """Main loop"""
    print_header()
    
    # Anslut till Modbus
    client = ModbusTcpClient('127.0.0.1', 502)
    if not client.connect():
        print("❌ Kunde inte ansluta till Modbus (127.0.0.1:502)")
        print("   Kör: sudo systemctl start unipi-modbus")
        return 1
    
    print("✅ Ansluten till Modbus\n")
    print("📊 Läser initial status...")
    
    last_bits = None
    update_interval = 0.2  # 200ms
    
    try:
        while True:
            bits = read_all_di(client)
            
            if bits is None:
                print("❌ Fel vid läsning av DI")
                time.sleep(1)
                continue
            
            # Skriv ut endast om status ändrats ELLER första gången
            if last_bits is None or bits != last_bits:
                print_status_table(bits, last_bits)
                last_bits = bits[:]
            
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("✅ MONITORING AVSLUTAT")
        print("="*80)
        
        # Visa slutstatus
        if last_bits:
            print("\n📊 SLUTSTATUS:")
            for i in range(12):
                status = "HIGH" if last_bits[i] else "LOW"
                print(f"   {DI_LABELS[i]}: {status}")
        
    finally:
        client.close()
        print("\n✅ Modbus-anslutning stängd\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
