#!/usr/bin/env python3
"""
relay_test.py - Hardware Test Script för Fotbollsplan Bevattning System 2.0

Detta script testar all hårdvara ansluten till PLC:n via Modbus:
- Relä 1-7 (ventiler)
- Relä 8 (pump) - endast om motorskydd (DI10) är OK
- Digitala ingångar (DI1-DI10)
- Analoga ingångar (MW30 markfukt, MW37 temperatur)

SÄKERHET:
- Motorskydd (DI10) verifieras INNAN pump-test
- DI10 hög = Motorskydd UTLÖST → Blockerar pump-test
- DI10 låg = Motorskydd OK → Tillåter pump-test

Användning:
    python3 relay_test.py --host <plc-ip>
    python3 relay_test.py --host 192.168.1.100 --skip-relays
    python3 relay_test.py --host 127.0.0.1 --force-pump-test  # FARLIGT!

Modbus-adresser:
- Coils (Outputs): 0-7 för Relä 1-8
- Discrete Inputs: 0-9 för DI1-DI10
- Holding Registers: MW30 (markfukt), MW37 (temperatur)
"""

import argparse
import sys
import time
from typing import Optional, Tuple

try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client.sync import ModbusTcpClient
    except ImportError:
        print("ERROR: pymodbus saknas. Installera: pip install pymodbus")
        sys.exit(1)

# Färgkoder för output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
MAGENTA = '\033[0;35m'
NC = '\033[0m'  # No Color

# Modbus-adresser
RELAY_COIL_START = 0  # R1-R8 = Coil 0-7
DI_INPUT_START = 0    # DI1-DI10 = Discrete Input 0-9
MW_MARKFUKT = 30      # Markfukt register
MW_TEMP = 37          # Temperatur register

# DI10 är motorskydd (KRITISK)
DI_MOTORSKYDD = 9  # DI10 = index 9 (0-based)

# Namn för digitala ingångar
DI_NAMES = {
    0: "DI1 - Stoppknapp",
    1: "DI2 - Startknapp",
    2: "DI3 - Nödstopp (NC)",
    3: "DI4 - Reset-knapp",
    4: "DI5 - Auto-läge knapp",
    5: "DI6 - Manual-läge knapp",
    6: "DI7 - Flödesvakt",
    7: "DI8 - Mjukstartare fel",
    8: "DI9 - Tryckvakt",
    9: "DI10 - Motorskydd (KRITISK)",
}

# Relä-namn
RELAY_NAMES = {
    0: "R1 - Ventil Zon 1",
    1: "R2 - Ventil Zon 2",
    2: "R3 - Ventil Zon 3",
    3: "R4 - Ventil Zon 4",
    4: "R5 - Ventil Zon 5",
    5: "R6 - Ventil Zon 6",
    6: "R7 - Ventil Zon 7",
    7: "R8 - Pump (via mjukstartare)",
}


def print_header(text: str) -> None:
    """Print formaterad header."""
    print(f"\n{BLUE}{'=' * 70}{NC}")
    print(f"{BLUE}  {text}{NC}")
    print(f"{BLUE}{'=' * 70}{NC}\n")


def print_success(text: str) -> None:
    """Print success-meddelande."""
    print(f"{GREEN}✓{NC} {text}")


def print_error(text: str) -> None:
    """Print error-meddelande."""
    print(f"{RED}✗{NC} {text}")


def print_warning(text: str) -> None:
    """Print warning-meddelande."""
    print(f"{YELLOW}⚠{NC} {text}")


def print_info(text: str) -> None:
    """Print info-meddelande."""
    print(f"{BLUE}ℹ{NC} {text}")


def connect_modbus(host: str, port: int, timeout: int = 5) -> Optional[ModbusTcpClient]:
    """
    Anslut till Modbus TCP.
    
    Returns:
        ModbusTcpClient om anslutning lyckades, None annars
    """
    print_info(f"Ansluter till Modbus TCP: {host}:{port}")
    
    try:
        client = ModbusTcpClient(host, port=port, timeout=timeout)
        if client.connect():
            print_success("Modbus-anslutning etablerad")
            return client
        else:
            print_error("Kunde inte ansluta till Modbus")
            return None
    except Exception as e:
        print_error(f"Modbus-anslutningsfel: {e}")
        return None


def read_discrete_input(client: ModbusTcpClient, address: int, unit: int = 1) -> Optional[bool]:
    """
    Läs en digital ingång.
    
    Returns:
        True/False om läsning lyckades, None vid fel
    """
    try:
        result = client.read_discrete_inputs(address, 1, unit=unit)
        if result.isError():
            return None
        return result.bits[0]
    except Exception as e:
        print_error(f"Fel vid läsning av DI{address + 1}: {e}")
        return None


def read_holding_register(client: ModbusTcpClient, address: int, unit: int = 1) -> Optional[int]:
    """
    Läs ett holding register.
    
    Returns:
        Register-värde om läsning lyckades, None vid fel
    """
    try:
        result = client.read_holding_registers(address, 1, unit=unit)
        if result.isError():
            return None
        return result.registers[0]
    except Exception as e:
        print_error(f"Fel vid läsning av MW{address}: {e}")
        return None


def write_coil(client: ModbusTcpClient, address: int, value: bool, unit: int = 1) -> bool:
    """
    Skriv till en coil (relä).
    
    Returns:
        True om skrivning lyckades, False vid fel
    """
    try:
        result = client.write_coil(address, value, unit=unit)
        if result.isError():
            return False
        return True
    except Exception as e:
        print_error(f"Fel vid skrivning till coil {address}: {e}")
        return False


def check_motorskydd(client: ModbusTcpClient, unit: int = 1) -> Tuple[bool, Optional[bool]]:
    """
    Kontrollera motorskydd (DI10).
    
    Returns:
        (safe: bool, di10_value: Optional[bool])
        safe = True om motorskydd är OK (DI10 låg)
        safe = False om motorskydd är utlöst (DI10 hög)
    """
    print_info("Kontrollerar motorskydd (DI10)...")
    
    di10_value = read_discrete_input(client, DI_MOTORSKYDD, unit)
    
    if di10_value is None:
        print_error("Kunde inte läsa motorskydd (DI10)")
        return False, None
    
    # DI10 hög = motorskydd UTLÖST
    # DI10 låg = motorskydd OK
    if di10_value:
        print_error("MOTORSKYDD UTLÖST (DI10 hög)")
        print_warning("Pump-test är BLOCKERAT av säkerhetsskäl")
        return False, di10_value
    else:
        print_success("Motorskydd OK (DI10 låg)")
        return True, di10_value


def test_relay(client: ModbusTcpClient, relay_num: int, unit: int = 1, duration: float = 2.0) -> bool:
    """
    Testa ett relä genom att aktivera i duration sekunder.
    
    Args:
        relay_num: Relä-nummer (1-8)
        duration: Tid i sekunder att hålla reläet aktiverat
    
    Returns:
        True om test lyckades, False vid fel
    """
    coil_address = relay_num - 1  # R1 = coil 0
    relay_name = RELAY_NAMES.get(coil_address, f"R{relay_num}")
    
    print(f"\n  Testar {relay_name}...")
    print(f"    Aktiverar i {duration} sekunder...")
    
    # Aktivera relä
    if not write_coil(client, coil_address, True, unit):
        print_error(f"    Misslyckades att aktivera {relay_name}")
        return False
    
    print_success(f"    {relay_name} aktiverat")
    print(f"    {YELLOW}Lyssna efter klick från reläet{NC}")
    
    time.sleep(duration)
    
    # Deaktivera relä
    if not write_coil(client, coil_address, False, unit):
        print_error(f"    Misslyckades att deaktivera {relay_name}")
        return False
    
    print_success(f"    {relay_name} deaktiverat")
    return True


def test_all_relays(client: ModbusTcpClient, unit: int = 1, skip_pump: bool = False,
                   force_pump: bool = False) -> dict:
    """
    Testa alla reläer.
    
    Args:
        skip_pump: Hoppa över pump-test (R8)
        force_pump: Tvinga pump-test även om motorskydd är utlöst (FARLIGT!)
    
    Returns:
        Dict med test-resultat
    """
    print_header("Relä-tester")
    
    results = {}
    
    # Testa ventiler (R1-R7)
    print_info("Testar ventiler (R1-R7)...")
    for relay_num in range(1, 8):
        success = test_relay(client, relay_num, unit, duration=2.0)
        results[f"R{relay_num}"] = success
        time.sleep(0.5)  # Kort paus mellan tester
    
    # Testa pump (R8) med motorskydd-check
    if not skip_pump:
        print(f"\n{MAGENTA}{'=' * 70}{NC}")
        print(f"{MAGENTA}  PUMP-TEST (R8){NC}")
        print(f"{MAGENTA}{'=' * 70}{NC}\n")
        
        if force_pump:
            print_warning("FORCE MODE: Hoppar över motorskydd-kontroll")
            print_warning("Detta är FARLIGT och bör endast användas för testning!")
            print()
            input(f"{RED}Tryck ENTER för att fortsätta eller Ctrl+C för att avbryta...{NC}")
            success = test_relay(client, 8, unit, duration=2.0)
            results["R8"] = success
        else:
            # Kontrollera motorskydd
            safe, di10_value = check_motorskydd(client, unit)
            
            if safe:
                print_success("Motorskydd OK - Pump-test tillåtet")
                print()
                input(f"{YELLOW}Tryck ENTER för att starta pump-test eller Ctrl+C för att avbryta...{NC}")
                success = test_relay(client, 8, unit, duration=2.0)
                results["R8"] = success
            else:
                print_error("Pump-test BLOCKERAT av motorskydd")
                print_info("Använd --force-pump-test för att tvinga (FARLIGT!)")
                results["R8"] = False
    else:
        print_info("Hoppar över pump-test (--skip-relays)")
        results["R8"] = None
    
    return results


def test_digital_inputs(client: ModbusTcpClient, unit: int = 1) -> dict:
    """
    Testa digitala ingångar interaktivt.
    
    Returns:
        Dict med test-resultat
    """
    print_header("Digitala Ingångar Test")
    
    print_info("Detta test läser alla digitala ingångar (DI1-DI10)")
    print_info("Du kan trigga knappar/sensorer manuellt och se värden i realtid")
    print()
    
    results = {}
    
    # Läs alla ingångar en gång
    print("Nuvarande status:")
    for di_index in range(10):
        di_num = di_index + 1
        di_name = DI_NAMES.get(di_index, f"DI{di_num}")
        
        value = read_discrete_input(client, di_index, unit)
        
        if value is None:
            print(f"  {di_name}: {RED}FEL{NC}")
            results[f"DI{di_num}"] = None
        else:
            status = f"{GREEN}HÖG{NC}" if value else f"{BLUE}LÅG{NC}"
            print(f"  {di_name}: {status}")
            results[f"DI{di_num}"] = value
            
            # Speciell varning för motorskydd
            if di_index == DI_MOTORSKYDD and value:
                print(f"    {RED}⚠ MOTORSKYDD UTLÖST!{NC}")
    
    print()
    print_info("Interaktiv test-läge")
    print("Tryck på knappar eller trigga sensorer för att se förändringar")
    print("Tryck Ctrl+C för att avsluta")
    print()
    
    try:
        previous_values = results.copy()
        
        while True:
            time.sleep(0.5)  # Poll varje halvsekund
            
            for di_index in range(10):
                di_num = di_index + 1
                di_name = DI_NAMES.get(di_index, f"DI{di_num}")
                
                value = read_discrete_input(client, di_index, unit)
                
                if value is None:
                    continue
                
                # Kolla om värdet har ändrats
                prev_key = f"DI{di_num}"
                if prev_key in previous_values and previous_values[prev_key] != value:
                    status = f"{GREEN}HÖG{NC}" if value else f"{BLUE}LÅG{NC}"
                    print(f"  {di_name}: {status}")
                    previous_values[prev_key] = value
                    
                    # Speciell varning för motorskydd
                    if di_index == DI_MOTORSKYDD and value:
                        print(f"    {RED}⚠ MOTORSKYDD UTLÖST!{NC}")
    
    except KeyboardInterrupt:
        print("\n")
        print_info("Avslutar interaktiv test-läge")
    
    return results


def test_analog_inputs(client: ModbusTcpClient, unit: int = 1) -> dict:
    """
    Testa analoga ingångar.
    
    Returns:
        Dict med test-resultat
    """
    print_header("Analoga Ingångar Test")
    
    results = {}
    
    # Läs markfukt (MW30)
    print_info("Läser markfukt (MW30)...")
    markfukt = read_holding_register(client, MW_MARKFUKT, unit)
    
    if markfukt is None:
        print_error("Kunde inte läsa MW30 (markfukt)")
        results["MW30_markfukt"] = None
    else:
        print_success(f"Markfukt: {markfukt}%")
        
        # Validera värde
        if 0 <= markfukt <= 100:
            print(f"  {GREEN}✓ Värde inom rimligt område (0-100%)%{NC}")
        else:
            print(f"  {YELLOW}⚠ Värde utanför rimligt område (0-100%){NC}")
        
        results["MW30_markfukt"] = markfukt
    
    # Läs temperatur (MW37)
    print()
    print_info("Läser jordtemperatur (MW37)...")
    temp_raw = read_holding_register(client, MW_TEMP, unit)
    
    if temp_raw is None:
        print_error("Kunde inte läsa MW37 (temperatur)")
        results["MW37_temp"] = None
    else:
        print_success(f"Jordtemperatur (råvärde): {temp_raw}")
        
        # Validera värde (råvärde 0-27648 enligt hardware_map.csv)
        if 0 <= temp_raw <= 27648:
            print(f"  {GREEN}✓ Råvärde inom rimligt område (0-27648){NC}")
            
            # Försök konvertera till grader (approximation)
            # Antag 0-27648 mappar till -20 till +50°C
            temp_celsius = (temp_raw / 27648.0) * 70 - 20
            print(f"  Approximerad temperatur: {temp_celsius:.1f}°C")
        else:
            print(f"  {YELLOW}⚠ Råvärde utanför rimligt område (0-27648){NC}")
        
        results["MW37_temp"] = temp_raw
    
    return results


def print_summary(relay_results: dict, di_results: dict, analog_results: dict) -> None:
    """Print sammanfattning av alla tester."""
    print_header("Test-sammanfattning")
    
    # Relä-resultat
    print(f"{BLUE}Relä-tester:{NC}")
    for relay, result in relay_results.items():
        if result is None:
            print(f"  {relay}: {YELLOW}HOPPADES ÖVER{NC}")
        elif result:
            print(f"  {relay}: {GREEN}OK{NC}")
        else:
            print(f"  {relay}: {RED}MISSLYCKADES{NC}")
    
    # Digitala ingångar
    print(f"\n{BLUE}Digitala ingångar:{NC}")
    for di, result in di_results.items():
        if result is None:
            print(f"  {di}: {RED}FEL{NC}")
        else:
            status = f"{GREEN}HÖG{NC}" if result else f"{BLUE}LÅG{NC}"
            print(f"  {di}: {status}")
    
    # Analoga ingångar
    print(f"\n{BLUE}Analoga ingångar:{NC}")
    for reg, result in analog_results.items():
        if result is None:
            print(f"  {reg}: {RED}FEL{NC}")
        else:
            print(f"  {reg}: {GREEN}{result}{NC}")
    
    # Total status
    print()
    relay_ok = sum(1 for r in relay_results.values() if r is True)
    relay_total = len([r for r in relay_results.values() if r is not None])
    
    di_ok = sum(1 for r in di_results.values() if r is not None)
    di_total = len(di_results)
    
    analog_ok = sum(1 for r in analog_results.values() if r is not None)
    analog_total = len(analog_results)
    
    print_success(f"Relä: {relay_ok}/{relay_total} OK")
    print_success(f"Digitala ingångar: {di_ok}/{di_total} läsbara")
    print_success(f"Analoga ingångar: {analog_ok}/{analog_total} läsbara")


def main():
    """Main-funktion."""
    parser = argparse.ArgumentParser(
        description="Hardware test för Fotbollsplan Bevattning System 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  python3 relay_test.py --host 192.168.1.100
  python3 relay_test.py --host 127.0.0.1 --skip-relays
  python3 relay_test.py --host 192.168.1.100 --force-pump-test  # FARLIGT!

SÄKERHET:
  Motorskydd (DI10) kontrolleras automatiskt innan pump-test.
  Använd --force-pump-test ENDAST för testning när du vet att det är säkert!
        """
    )
    
    parser.add_argument("--host", default="127.0.0.1", help="Modbus TCP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=502, help="Modbus TCP port (default: 502)")
    parser.add_argument("--unit", type=int, default=1, help="Modbus Unit ID (default: 1)")
    parser.add_argument("--skip-relays", action="store_true", help="Hoppa över relätester")
    parser.add_argument("--skip-inputs", action="store_true", help="Hoppa över ingångstester")
    parser.add_argument("--skip-analog", action="store_true", help="Hoppa över analoga tester")
    parser.add_argument("--force-pump-test", action="store_true",
                       help="FARLIG - Tvinga pump-test även om motorskydd är utlöst")
    
    args = parser.parse_args()
    
    # Banner
    print_header("Fotbollsplan Bevattning System 2.0 - Hardware Test")
    print(f"Modbus TCP: {args.host}:{args.port}")
    print(f"Unit ID: {args.unit}")
    print()
    
    # Anslut till Modbus
    client = connect_modbus(args.host, args.port)
    if not client:
        print_error("Kunde inte ansluta till PLC")
        return 1
    
    try:
        relay_results = {}
        di_results = {}
        analog_results = {}
        
        # Relä-tester
        if not args.skip_relays:
            relay_results = test_all_relays(
                client, args.unit,
                skip_pump=False,
                force_pump=args.force_pump_test
            )
        
        # Digital inputs test
        if not args.skip_inputs:
            di_results = test_digital_inputs(client, args.unit)
        
        # Analog inputs test
        if not args.skip_analog:
            analog_results = test_analog_inputs(client, args.unit)
        
        # Sammanfattning
        print_summary(relay_results, di_results, analog_results)
        
        print()
        print_success("Hårdvarutest klart!")
        
    except KeyboardInterrupt:
        print("\n")
        print_info("Test avbrutet av användare")
    
    finally:
        client.close()
        print_info("Modbus-anslutning stängd")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
