#!/usr/bin/env python3
"""
Säker relätest - Aktiverar varje relä EN i taget
ANVÄND DETTA ENDAST UTAN VATTEN I SYSTEMET!
"""
import time
import sys
from pymodbus.client import ModbusTcpClient

RELAY_NAMES = {
    0: "R1 - PUMP",
    1: "R2 - Ventil Zon 1",
    2: "R3 - Ventil Zon 2",
    3: "R4 - Ventil Zon 3",
    4: "R5 - Reserved",
    5: "R6 - Reserved",
    6: "R7 - Reserved",
    7: "R8 - Reserved"
}

def test_relay(client, relay_num, duration=2.0):
    """
    Testa ett enskilt relä
    
    Args:
        client: Modbus client
        relay_num: Relänummer (0-7)
        duration: Hur länge reläet ska vara aktiverat (sekunder)
    """
    relay_name = RELAY_NAMES.get(relay_num, f"R{relay_num+1}")
    
    print(f"\n{'='*60}")
    print(f"TEST: {relay_name}")
    print(f"{'='*60}")
    
    # Verifiera att reläet är av först
    result = client.read_coils(relay_num, 1, slave=1)
    if result.isError():
        print(f"❌ Fel vid läsning av relä {relay_num}")
        return False
    
    if result.bits[0]:
        print(f"⚠️  Varning: Reläet är redan AKTIVT! Stänger av det först...")
        client.write_coil(relay_num, False, slave=1)
        time.sleep(0.5)
    
    # Aktivera reläet
    print(f"🔌 Aktiverar {relay_name}...")
    client.write_coil(relay_num, True, slave=1)
    
    # Verifiera att det aktiverades
    result = client.read_coils(relay_num, 1, slave=1)
    if result.bits[0]:
        print(f"✅ Reläet AKTIVERAT - Lyssna efter 'klick'")
    else:
        print(f"❌ MISSLYCKADES att aktivera reläet!")
        return False
    
    # Vänta
    for i in range(int(duration)):
        print(f"   ... {duration - i}s kvar", end='\r')
        time.sleep(1)
    
    # Stäng av
    print(f"\n🔌 Stänger av {relay_name}...")
    client.write_coil(relay_num, False, slave=1)
    
    # Verifiera att det stängdes av
    result = client.read_coils(relay_num, 1, slave=1)
    if not result.bits[0]:
        print(f"✅ Reläet AVSTÄNGT")
        return True
    else:
        print(f"❌ MISSLYCKADES att stänga av reläet!")
        return False

def main():
    print("\n" + "="*60)
    print("SÄKER RELÄTEST - Fotbollsplan Bevattning")
    print("="*60)
    print("\n⚠️  SÄKERHETSVARNING:")
    print("   - Kör ENDAST detta test UTAN vatten i systemet")
    print("   - Reläerna aktiveras EN i taget i 2 sekunder")
    print("   - Lyssna efter 'klick'-ljud från varje relä")
    print("   - Tryck Ctrl+C för att avbryta när som helst\n")
    
    input("Tryck ENTER för att fortsätta eller Ctrl+C för att avbryta...")
    
    # Anslut till Modbus
    client = ModbusTcpClient('127.0.0.1', 502)
    if not client.connect():
        print("❌ Kunde inte ansluta till Modbus (127.0.0.1:502)")
        return 1
    
    print("\n✅ Ansluten till Modbus\n")
    
    # Läs alla reläer först
    print("📊 Kontrollerar alla reläer innan test...")
    result = client.read_coils(0, 8, slave=1)
    if not result.isError():
        for i in range(8):
            status = "ON 🟢" if result.bits[i] else "OFF ⚫"
            print(f"   {RELAY_NAMES[i]}: {status}")
    
    # Stäng av alla reläer först
    print("\n🔌 Stänger av alla reläer innan test...")
    for i in range(8):
        client.write_coil(i, False, slave=1)
    time.sleep(1)
    
    # Testa ALLA reläer R1-R8
    test_relays = [0, 1, 2, 3, 4, 5, 6, 7]  # R1-R8
    
    try:
        for relay_num in test_relays:
            result = test_relay(client, relay_num, duration=2.0)
            if not result:
                print(f"\n⚠️  Test av relä {relay_num} misslyckades!")
            time.sleep(1)  # Paus mellan tester
        
        print("\n" + "="*60)
        print("✅ RELÄTEST SLUTFÖRT")
        print("="*60)
        print("\nResultat:")
        print("  - Om du hörde 'klick' från varje relä = OK")
        print("  - Om inget ljud = Kontrollera hårdvarukopplingar")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test avbrutet av användare")
    finally:
        # Säkerställ att alla reläer är av
        print("\n🔒 Stänger av alla reläer...")
        for i in range(8):
            client.write_coil(i, False, slave=1)
        client.close()
        print("✅ Modbus-anslutning stängd\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
