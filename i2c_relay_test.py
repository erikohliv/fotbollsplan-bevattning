#!/usr/bin/env python3
"""
Direkt I2C Relätest - Kör igenom alla reläer
"""
import smbus2
import time
import sys

MCP23008_ADDR = 0x20

def relay_test():
    print("\n" + "="*60)
    print("🔧 DIREKT I2C RELÄTEST")
    print("="*60)
    print("\nDetta testar alla 8 reläer direkt via I2C")
    print("Varje relä aktiveras i 3 sekunder")
    print("\n⚠️  LYSSNA efter klick-ljud från reläerna!")
    print("="*60)
    
    input("\n👉 Tryck ENTER för att ge KLARTECKEN och starta nedräkning...")
    
    # Nedräkning 20 sekunder
    print("\n🕐 NEDRÄKNING STARTAR:\n")
    for i in range(20, 0, -1):
        print(f"    ⏱  {i:2d} sekunder kvar...  ", end='\r')
        sys.stdout.flush()
        time.sleep(1)
    
    print("\n\n" + "="*60)
    print("🚀 SEKVENS STARTAR NU!")
    print("="*60 + "\n")
    time.sleep(0.5)
    
    # Öppna I2C bus
    bus = smbus2.SMBus(1)
    
    try:
        # Konfigurera MCP23008 som utgångar
        bus.write_byte_data(MCP23008_ADDR, 0x00, 0x00)  # IODIR = alla utgångar
        print("✅ MCP23008 konfigurerad\n")
        time.sleep(0.5)
        
        # Test reläer 1-8
        for relay_num in range(1, 9):
            bit_mask = 1 << (relay_num - 1)
            
            if relay_num <= 7:
                print(f"⚡ ZON {relay_num} → Relä {relay_num} ON")
            else:
                print(f"⚡ PUMP → Relä {relay_num} ON")
            
            # Aktivera relä
            bus.write_byte_data(MCP23008_ADDR, 0x09, bit_mask)
            print(f"   🔊 LYSSNA PÅ KLICK!")
            time.sleep(3)
            
            # Stäng av
            bus.write_byte_data(MCP23008_ADDR, 0x09, 0x00)
            print(f"   ✅ Relä {relay_num} OFF\n")
            time.sleep(0.5)
        
        print("="*60)
        print("✅ SEKVENS KLAR!")
        print("="*60)
        print("\nResultat:")
        print("  Hörde du klick från alla 8 reläer?")
        print("  • Relä 1-7: Zonventiler")
        print("  • Relä 8: Pump")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ FEL: {e}")
        bus.write_byte_data(MCP23008_ADDR, 0x09, 0x00)
    finally:
        bus.close()

if __name__ == "__main__":
    try:
        relay_test()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test AVBRUTET!")
        try:
            bus = smbus2.SMBus(1)
            bus.write_byte_data(MCP23008_ADDR, 0x09, 0x00)
            bus.close()
            print("🛑 Alla reläer avstängda")
        except:
            pass
        sys.exit(0)
