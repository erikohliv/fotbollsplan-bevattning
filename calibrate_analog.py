#!/usr/bin/env python3
"""
Kalibreringsverktyg för Analoga Enheter
Testar och kalibrerar AI1 (Markfukt) och AI2 (Jordtemperatur)
"""
import sys
import time
from pymodbus.client import ModbusTcpClient

MODBUS_HOST = "127.0.0.1"
MODBUS_PORT = 502
MODBUS_UNIT = 1

# Modbus-register
INPUT_REG_AI1 = 0  # AI1 (Markfukt) - Input Register 0
INPUT_REG_AI2 = 1  # AI2 (Temperatur) - Input Register 1


def read_analog_input(client, channel):
    """Läs analog ingång via Modbus"""
    reg = INPUT_REG_AI1 if channel == 1 else INPUT_REG_AI2
    rr = client.read_input_registers(reg, 1, device_id=MODBUS_UNIT)
    if rr.isError():
        return None
    return rr.registers[0]


def voltage_from_modbus(modbus_value):
    """Konvertera Modbus-värde (0-10000) till spänning (0-10V)"""
    return (modbus_value / 10000.0) * 10.0


def print_header(text):
    """Print en rubrik"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_analog_inputs():
    """Testa analoga ingångar"""
    print_header("KALIBRERING AV ANALOGA ENHETER")
    
    print("\n📋 Instruktioner:")
    print("   1. Kontrollera att 24V är på")
    print("   2. Kontrollera att sensorerna är anslutna")
    print("   3. För verifiering: Anslut känd spänning (0-10V)")
    print("   4. Tryck Ctrl+C för att avsluta\n")
    
    try:
        client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
        if not client.connect():
            print("❌ Kunde inte ansluta till Modbus-server")
            print(f"   Kontrollera att unipi-modbus-server körs på {MODBUS_HOST}:{MODBUS_PORT}")
            return
        
        print("✅ Ansluten till Modbus-server\n")
        
        print("Läser analoga ingångar var 2:a sekund...")
        print("Tryck Ctrl+C för att avsluta\n")
        
        print(f"{'Tid':<10} {'AI1 (Markfukt)':<25} {'AI2 (Temperatur)':<25}")
        print(f"{'':<10} {'Modbus':<10} {'Voltage':<10} {'Modbus':<10} {'Voltage':<10}")
        print("-" * 70)
        
        while True:
            # Läs AI1 (Markfukt)
            ai1_value = read_analog_input(client, 1)
            ai1_voltage = voltage_from_modbus(ai1_value) if ai1_value is not None else 0.0
            ai1_percent = (ai1_value / 10000.0) * 100.0 if ai1_value is not None else 0.0
            
            # Läs AI2 (Temperatur)
            ai2_value = read_analog_input(client, 2)
            ai2_voltage = voltage_from_modbus(ai2_value) if ai2_value is not None else 0.0
            
            # Beräkna temperatur (exempel: 0V=-50°C, 10V=+150°C)
            # Justera dessa värden baserat på din sensormodell!
            temp_min = -50.0  # Temperatur vid 0V
            temp_max = 150.0  # Temperatur vid 10V
            temp_range = temp_max - temp_min
            temperature = temp_min + (ai2_voltage / 10.0) * temp_range if ai2_value is not None else 0.0
            
            timestamp = time.strftime("%H:%M:%S")
            
            print(f"{timestamp:<10} "
                  f"{ai1_value if ai1_value is not None else 'ERR':<10} "
                  f"{ai1_voltage:.2f}V ({ai1_percent:.1f}%){'':<5} "
                  f"{ai2_value if ai2_value is not None else 'ERR':<10} "
                  f"{ai2_voltage:.2f}V ({temperature:.1f}°C)")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n✅ Avslutar kalibrering")
    except Exception as e:
        print(f"\n❌ Fel: {e}")
    finally:
        if client:
            client.close()


def verify_voltage_source():
    """Verifiera med känd spänningskälla"""
    print_header("VERIFIERING MED KÄND SPÄNNING")
    
    print("\n📋 Instruktioner:")
    print("   Anslut en variabel spänningskälla (0-10V) till AI1 eller AI2")
    print("   Testa följande spänningar och verifiera att Modbus-värden stämmer:\n")
    
    test_voltages = [0.0, 2.5, 5.0, 7.5, 10.0]
    expected_modbus = {v: int((v / 10.0) * 10000) for v in test_voltages}
    
    print(f"{'Spänning':<12} {'Förväntat Modbus':<20} {'Tolerans':<15}")
    print("-" * 50)
    for voltage in test_voltages:
        expected = expected_modbus[voltage]
        print(f"{voltage:>5.1f}V{'':<6} {expected:>8}{'':<11} ±200")
    
    print("\nTryck Enter när du är redo att börja testa...")
    input()
    
    try:
        client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
        if not client.connect():
            print("❌ Kunde inte ansluta till Modbus-server")
            return
        
        print("\nVilken kanal vill du testa? (1=AI1 Markfukt, 2=AI2 Temperatur)")
        channel = input("Kanal: ").strip()
        
        if channel not in ['1', '2']:
            print("❌ Ogiltig kanal")
            return
        
        channel = int(channel)
        channel_name = "AI1 (Markfukt)" if channel == 1 else "AI2 (Temperatur)"
        
        print(f"\nTestar {channel_name}...")
        print("Sätt spänningen enligt tabellen ovan och tryck Enter efter varje mätning\n")
        
        results = []
        for voltage in test_voltages:
            print(f"Sätt spänningen till {voltage:.1f}V och tryck Enter...")
            input()
            
            value = read_analog_input(client, channel)
            if value is None:
                print("  ❌ Kunde inte läsa värde")
                continue
            
            measured_voltage = voltage_from_modbus(value)
            error = abs(measured_voltage - voltage)
            
            status = "✅" if error < 0.2 else "⚠️"
            print(f"  {status} Modbus: {value}, Voltage: {measured_voltage:.2f}V, Fel: {error:.2f}V")
            
            results.append({
                'expected': voltage,
                'modbus': value,
                'measured': measured_voltage,
                'error': error
            })
        
        print("\n" + "=" * 60)
        print("SAMMANFATTNING:")
        print("=" * 60)
        print(f"{'Förväntat':<12} {'Modbus':<10} {'Mätt':<12} {'Fel':<12} {'Status':<10}")
        print("-" * 60)
        
        for r in results:
            status = "✅ OK" if r['error'] < 0.2 else "⚠️ AVVIKELSE"
            print(f"{r['expected']:>5.1f}V{'':<6} "
                  f"{r['modbus']:>8}{'':<1} "
                  f"{r['measured']:>6.2f}V{'':<5} "
                  f"{r['error']:>6.2f}V{'':<5} "
                  f"{status}")
        
        max_error = max([r['error'] for r in results])
        if max_error < 0.2:
            print("\n✅ Alla mätningar är inom tolerans (±0.2V)")
        else:
            print(f"\n⚠️ Vissa mätningar avviker mer än ±0.2V")
            print("   Kontrollera spänningsdelare och kabelanslutningar")
        
    except KeyboardInterrupt:
        print("\n\n✅ Avslutar verifiering")
    except Exception as e:
        print(f"\n❌ Fel: {e}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_voltage_source()
    else:
        test_analog_inputs()

