#!/usr/bin/env python3
"""
I2C Bus Monitor - Övervaka I2C-trafik och ändringar
"""
import smbus2
import time
import sys

def scan_i2c_devices(bus):
    """Hitta alla I2C-devices"""
    devices = []
    for addr in range(0x03, 0x78):
        try:
            bus.read_byte(addr)
            devices.append(addr)
        except:
            pass
    return devices

def monitor_i2c(duration=10):
    print("\n" + "="*70)
    print("🔍 I2C BUS MONITOR - Övervakning i {} sekunder".format(duration))
    print("="*70)
    
    bus = smbus2.SMBus(1)
    
    # Hitta alla devices
    print("\n📡 Scannar I2C-bussen...")
    devices = scan_i2c_devices(bus)
    
    print(f"\n✅ Hittade {len(devices)} devices:")
    for addr in devices:
        device_name = {
            0x20: "MCP23008 (Reläer)",
            0x27: "LCD Display / PCF8574",
            0x3C: "OLED Display",
            0x3D: "OLED Display",
            0x50: "EEPROM",
            0x57: "EEPROM (Alt)",
            0x68: "RTC (DS1307)",
            0x6F: "MCP7941x RTC"
        }.get(addr, "Okänd")
        print(f"  • 0x{addr:02X} ({addr}) - {device_name}")
    
    # Övervaka display (0x27) om den finns
    if 0x27 in devices:
        print(f"\n📺 Övervakar LCD Display (0x27) i {duration} sekunder...")
        print("   (Loggar alla ändringar)\n")
        
        last_value = None
        start_time = time.time()
        changes = 0
        
        while time.time() - start_time < duration:
            try:
                value = bus.read_byte(0x27)
                if value != last_value and last_value is not None:
                    changes += 1
                    elapsed = time.time() - start_time
                    print(f"  [{elapsed:5.2f}s] 0x27: 0x{last_value:02X} → 0x{value:02X} (bin: {value:08b})")
                last_value = value
            except Exception as e:
                print(f"  Läsfel: {e}")
            time.sleep(0.1)
        
        print(f"\n✅ Monitorering klar - {changes} ändringar detekterade")
    
    # Kolla register 57 specifikt (om EEPROM)
    if 0x57 in devices or 0x50 in devices:
        print("\n📝 Kollar EEPROM-register...")
        for eeprom_addr in [0x50, 0x57]:
            if eeprom_addr in devices:
                try:
                    # Läs första 16 bytes
                    data = []
                    for i in range(16):
                        try:
                            byte = bus.read_byte_data(eeprom_addr, i)
                            data.append(byte)
                        except:
                            data.append(None)
                    
                    print(f"\n  EEPROM 0x{eeprom_addr:02X} - Första 16 bytes:")
                    print("  Addr: " + " ".join([f"{i:02X}" for i in range(16)]))
                    print("  Data: " + " ".join([f"{b:02X}" if b is not None else "XX" for b in data]))
                except Exception as e:
                    print(f"  Kunde inte läsa från 0x{eeprom_addr:02X}: {e}")
    
    # Sammanfattning
    print("\n" + "="*70)
    print("📊 SAMMANFATTNING")
    print("="*70)
    print(f"  Aktiva I2C-devices: {len(devices)}")
    print(f"  Adresser: {', '.join([f'0x{a:02X}' for a in devices])}")
    
    if 0x27 in devices:
        print(f"\n  💡 Tips för LCD 0x27:")
        print("     - Kan vara LCD1602/2004 med I2C-adapter")
        print("     - Konstiga symboler = Fel initiering eller data")
        print("     - Behöver rätt timing och kommandon")
    
    print("\n")
    bus.close()

if __name__ == "__main__":
    try:
        duration = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        monitor_i2c(duration)
    except KeyboardInterrupt:
        print("\n\n⚠️  Avbrutet av användare")
    except Exception as e:
        print(f"\n❌ Fel: {e}")
