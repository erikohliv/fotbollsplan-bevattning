#!/usr/bin/env python3
"""
Test script för arkadknappar
Tryck på varje knapp för att verifiera att den fungerar
"""
import time
try:
    import smbus2 as smbus
except ImportError:
    import smbus

def read_buttons(bus, addr=0x20):
    """
    Läs knapptryckningar från PCF8574
    P0 = UP, P1 = DOWN, P2 = LEFT, P3 = OK
    Active LOW: Pressed = 0
    """
    try:
        data = bus.read_byte(addr)
        return {
            'up': not bool(data & 0x01),
            'down': not bool(data & 0x02),
            'left': not bool(data & 0x04),
            'ok': not bool(data & 0x08)
        }
    except Exception as e:
        print(f"Fel vid läsning: {e}")
        return {'up': False, 'down': False, 'left': False, 'ok': False}

def main():
    print("=" * 50)
    print("ARKADKNAPPS-TEST")
    print("=" * 50)
    print("\nTryck på varje knapp för att testa:")
    print("  UP    = P0 (bit 0)")
    print("  DOWN  = P1 (bit 1)")
    print("  LEFT  = P2 (bit 2)")
    print("  OK    = P3 (bit 3)")
    print("\nTryck Ctrl+C för att avsluta\n")
    
    bus = smbus.SMBus(1)
    
    # Testa båda adresserna
    addresses = [0x20, 0x21]
    
    for addr in addresses:
        print(f"\n🔍 Testar adress 0x{addr:02X}...")
        try:
            data = bus.read_byte(addr)
            print(f"   ✅ Hittad! Raw byte: 0x{data:02X} (binary: {bin(data)})")
        except:
            print(f"   ❌ Ingen enhet på denna adress")
            continue
    
    print("\n" + "=" * 50)
    print("LIVE BUTTON MONITOR (Ctrl+C för att avsluta)")
    print("=" * 50)
    
    # Använd första fungerande adressen
    working_addr = 0x20
    try:
        bus.read_byte(working_addr)
    except:
        working_addr = 0x21
    
    last_buttons = {'up': False, 'down': False, 'left': False, 'ok': False}
    
    try:
        while True:
            buttons = read_buttons(bus, working_addr)
            
            # Visa endast när status ändras
            if buttons != last_buttons:
                status_line = []
                for name, pressed in buttons.items():
                    if pressed:
                        status_line.append(f"[{name.upper()}]")
                    else:
                        status_line.append(f" {name.upper()} ")
                
                print(f"\r{'  '.join(status_line)}", end='', flush=True)
                
                # Om knapp trycktes, visa på ny rad
                if any(buttons.values()):
                    pressed_buttons = [k.upper() for k, v in buttons.items() if v]
                    print(f"\n🔘 TRYCKT: {', '.join(pressed_buttons)}")
                
                last_buttons = buttons.copy()
            
            time.sleep(0.05)  # 50ms polling
            
    except KeyboardInterrupt:
        print("\n\n✅ Test avslutat")
    finally:
        bus.close()

if __name__ == "__main__":
    main()
