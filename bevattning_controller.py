#!/usr/bin/env python3
"""
Bevattning_controller.py (uppdaterad)
- Hämtar väder från Open-Meteo, valfritt markfukt via Modbus.
- Skriver temp/regn/markfukt/tider till PLC via Modbus.
- Pulserar Remote_Command (MW10) vid behov.
- Fallback och begränsning av rimliga värden.
- Kan köras en gång eller i loop.
- Stöd för zon-exkludering via zone_config.py
"""
from datetime import datetime
import time
import os
import csv
import argparse
import logging
import requests
from dotenv import load_dotenv

# Ladda environment-variabler från api_.env
load_dotenv("api_.env")

# Import zone configuration handler
try:
    from zone_config import ZoneConfig
    HAS_ZONE_CONFIG = True
except ImportError:
    HAS_ZONE_CONFIG = False
    logging.warning("zone_config.py saknas, alla zoner kommer köras")

# Import pump protection module
from pump_protection import PumpState, check_pump_safety, get_diagnostics

try:
    from pymodbus.client import ModbusTcpClient
except Exception:
    try:
        from pymodbus.client.sync import ModbusTcpClient
    except Exception:
        ModbusTcpClient = None

# API och Modbus-konfiguration från environment
API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')
API_KEY = os.getenv('API_KEY', '')
DEFAULT_MODBUS_HOST = os.getenv('MODBUS_HOST', '127.0.0.1')
DEFAULT_MODBUS_PORT = int(os.getenv('MODBUS_PORT', '502'))
DEFAULT_MODBUS_UNIT = int(os.getenv('MODBUS_UNIT', '1'))

LOG_FIL = os.path.join(os.path.expanduser("~"), "bevattning_log.csv")
# Default coordinates for Håkanryd, Bromölla
DEFAULT_LATITUDE = "56.05"    # Håkanryd, Bromölla
DEFAULT_LONGITUDE = "14.40"   # Håkanryd, Bromölla
FORECAST_HOURS = 24

BASE_TID_CENTER = 60   # minuter per center-zon
BASE_TID_HORN = 25     # minuter per hörn-zon

GRANS_REGN_PROGNOS = 5.0
GRANS_TEMP_MIN = 10.0

MW_REMOTE_CMD = 10
MW_TID_CENTER = 20
MW_TID_HORN = 21
MW_MARKFUKT = 30
MW_REGEN24 = 31
MW_TEMP = 32
MW_PRESSURE_SWITCH = 33      # Tryckvakt status (0=ingen tryck, 1=tryck OK)
MW_SOIL_TEMP_RAW = 37        # Jordtemperatur råvärde från analog A2 (0-27648 motsvarar 0-10V)
MW_STATUS_PUMP = 51          # Signal_Pump status (1=running, 0=stopped)
MW_FLOW_SWITCH = 55          # FlowSwitchStatus (1=flow, 0=no flow)
MW_BLOCK_REASON = 73  # BlockReasonReg: 0=OK, 1=Rain, 2=Moisture, 3=Anti-collision, 4=E-stop, 5=Pressure, 6=Flow, 7=Motor protection, 8=Soft starter fault, 9=24VDC fuse, 10=24VAC fuse, 11=Slangbrott, 12=Torrkörning

MK_REG_ADDR = 100  # exempelfält för extern markfukt-läsning

# Digital Inputs - Säkringsövervakning
DI_FUSE_24VDC = 10   # %IX1.2 = I11 - 24VDC säkring (PLC, sensorer)
DI_FUSE_24VAC = 11   # %IX1.3 = I12 - 24VAC säkring (ventiler) - FÖRBERED

# Block Reason Codes
BLOCK_REASON_FUSE_24VDC = 9   # 24VDC säkring utlöst
BLOCK_REASON_FUSE_24VAC = 10  # 24VAC säkring utlöst (framtida)

# Weather cache to avoid excessive API calls in loop mode.
# Simple global cache is sufficient for single-threaded controller script.
# For multi-threaded use, consider thread-safe caching library.
_weather_cache = {"data": None, "timestamp": None, "cache_duration": 600}  # 10 minutes cache

# Global state for pump protection (persistent between körningar i loop mode)
_pump_state = PumpState()

logger = logging.getLogger("bevattning")
logger.setLevel(logging.DEBUG)
_formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
_console = logging.StreamHandler()
_console.setFormatter(_formatter)
_console.setLevel(logging.INFO)
logger.addHandler(_console)


def open_modbus_client(host, port, timeout=5):
    if ModbusTcpClient is None:
        raise RuntimeError("pymodbus saknas (pip install pymodbus).")
    client = ModbusTcpClient(host, port=port, timeout=timeout)
    return client


def hamta_vader(lat, lon, timeout=10, use_cache=True):
    """
    Hämtar väderdata från Open-Meteo API.
    Returnerar aktuell temperatur och total nederbörd kommande 24h.
    Cache reduces API calls in loop mode.
    """
    # Check cache first
    if use_cache and _weather_cache["data"] is not None and _weather_cache["timestamp"] is not None:
        age = time.time() - _weather_cache["timestamp"]
        if age < _weather_cache["cache_duration"]:
            logger.debug("Using cached weather data (age: %.1f seconds)", age)
            return _weather_cache["data"]
    
    try:
        latitude = float(lat)
        longitude = float(lon)
    except (TypeError, ValueError):
        logger.warning("Ogiltiga koordinater lat=%s lon=%s", lat, lon)
        return None, None

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,rain",
            "current_weather": True,
            "timezone": "auto",
        }
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        hourly = data.get("hourly", {})
        rain_list = hourly.get("rain") or []
        temp_list = hourly.get("temperature_2m") or []

        if not rain_list:
            logger.warning("Open-Meteo saknar regndata i svar, kan inte beräkna regn.")
            return None, None
        if len(rain_list) < FORECAST_HOURS:
            logger.warning("Open-Meteo gav endast %d timmar regndata, avbryter.", len(rain_list))
            return None, None

        timmar_att_summera = min(len(rain_list), FORECAST_HOURS)
        total_regn = sum(float(x or 0.0) for x in rain_list[:timmar_att_summera])

        temp_nu = data.get("current_weather", {}).get("temperature")
        if temp_nu is None and len(temp_list) > 0 and temp_list[0] is not None:
            # Använd första timprognosen som rimlig fallback om current_weather saknas.
            temp_nu = float(temp_list[0])
        if temp_nu is None:
            temp_nu = 15.0
        else:
            temp_nu = float(temp_nu)

        # Beräkna total nederbörd för kommande 24h
        hourly_precip = data.get("hourly", {}).get("precipitation", [])
        if hourly_precip:
            # Ta första 24 timmarna
            total_regn = sum(float(p or 0.0) for p in hourly_precip[:24])
        else:
            total_regn = 0.0

        # Rimliga gränser
        temp_nu = max(-30.0, min(50.0, temp_nu))
        total_regn = max(0.0, min(500.0, total_regn))

        result = (temp_nu, total_regn)
        
        # Update cache
        if use_cache:
            _weather_cache["data"] = result
            _weather_cache["timestamp"] = time.time()
            logger.debug("Weather data cached")
        
        return result
    except Exception as e:
        logger.warning("Kunde inte hämta väder från Open-Meteo: %s", e)
        # Return cached data if available even if expired
        if _weather_cache["data"] is not None:
            logger.info("Using expired cached weather data due to API error")
            return _weather_cache["data"]
        return None, None


def read_markfukt_from_modbus(addr, host, port, unit=DEFAULT_MODBUS_UNIT):
    if ModbusTcpClient is None:
        logger.debug("pymodbus ej tillgängligt.")
        return None
    client = open_modbus_client(host, port)
    try:
        if not client.connect():
            logger.warning("Kunde inte ansluta för markfukt-read.")
            return None
        rr = client.read_holding_registers(addr, 1, unit=unit)
        client.close()
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            return None
        regs = getattr(rr, "registers", None)
        if regs:
            return int(regs[0])
        return None
    except Exception as e:
        logger.warning("Fel vid Modbus-read markfukt: %s", e)
        try:
            client.close()
        except Exception:
            pass
        return None


def check_season():
    """
    Kontrollera säsong och returnera varningar/blockeringar
    
    Returns:
        tuple: (block: bool, warning: str or None)
    """
    now = datetime.now()
    month = now.month
    day = now.day
    
    # Vinterperiod: December - Mars (inga bevattningar)
    if month in [12, 1, 2, 3]:
        return True, f"VINTER: Bevattning blockerad månad {month}. Systemet ska vara vinterberedt."
    
    # Oktober: Varning för blowout
    if month == 10:
        if day >= 15:
            warning = f"HÖST: Varning! Blowout bör genomföras senast 31 oktober. Idag: {now.strftime('%Y-%m-%d')}"
            logger.warning(warning)
            return False, warning
    
    # April: Säsongsstart-varning
    if month == 4:
        warning = "VÅR: Säsongstart. Kontrollera att systemet är aktiverat och testat."
        logger.info(warning)
        return False, warning
    
    return False, None


def check_sensor_voltage(sensor_value_raw: int, sensor_type: str, max_value: int = 27648) -> tuple:
    """
    Kontrollera om sensor-signal är giltig (>= 1.0V).
    
    OBS: Denna funktion används för råa analog-värden (0-27648 motsvarar 0-10V).
    För sensor-register som redan lagrar konverterade %-värden (t.ex. MW_MARKFUKT),
    använd istället tröskel-baserad validering (se main_once()).
    
    Args:
        sensor_value_raw: Råvärde från sensor (0-27648 för analog 0-10V)
        sensor_type: Sensor-namn för loggning ("Markfukt", "Temperatur")
        max_value: Max råvärde (default 27648 motsvarar 10V)
    
    Returns:
        (ok: bool, voltage: float)
        - ok=True: Signal >= 1.0V
        - ok=False: Signal < 1.0V (kabelbrott/fel)
    
    Användning:
        - Temperatur sensor (MW_SOIL_TEMP_RAW): check_sensor_voltage(temp_raw, "Temperatur", 27648)
        - Framtida: Markfukt råvärde från %IW0 om tillgängligt
    """
    voltage = (sensor_value_raw / max_value) * 10.0
    
    if voltage < 1.0:
        logger.error("🚨 SENSORFEL: %s signal %.2fV < 1.0V (Kabelbrott/Fel?)", sensor_type, voltage)
        logger.error("   → Automatik stoppad")
        logger.error("   → Använd '/command/start-fallback' för manuell körning")
        return False, voltage
    
    logger.debug("✅ %s sensor OK: %.2fV", sensor_type, voltage)
    return True, voltage


def check_power_fuses(client, unit=DEFAULT_MODBUS_UNIT) -> tuple:
    """
    Kontrollera båda säkringarna (24VDC och 24VAC).
    
    Returns:
        (ok: bool, reason: str, block_code: int)
        - ok=True: Alla säkringar OK
        - ok=False + reason + block_code: Vilken säkring som utlöst
    """
    try:
        # Läs båda discrete inputs samtidigt (I11-I12)
        rr = client.read_discrete_inputs(DI_FUSE_24VDC, 2, unit=unit)
        
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            logger.warning("Kunde inte läsa säkrings-status")
            return True, "OK", 0  # Fail-safe: tillåt körning om läsning misslyckas
        
        fuse_24vdc = rr.bits[0]  # I11
        fuse_24vac = rr.bits[1]  # I12
        
        # Kontrollera 24VDC (PLC/Sensorer) - KRITISKT
        if not fuse_24vdc:
            logger.error("🚨 KRITISKT: 24VDC säkring utlöst (I11=0)")
            logger.error("   → PLC, sensorer och styrning påverkad!")
            logger.error("   → Kontrollera säkringsautomater och elkoppling")
            return False, "24VDC säkring utlöst", BLOCK_REASON_FUSE_24VDC
        
        # Kontrollera 24VAC (Ventiler) - KRITISKT
        if not fuse_24vac:
            logger.error("🚨 KRITISKT: 24VAC säkring utlöst (I12=0)")
            logger.error("   → Solenoid-ventiler (R1-R7) fungerar EJ!")
            logger.error("   → Kontrollera säkringsautomater för 24VAC")
            return False, "24VAC säkring utlöst", BLOCK_REASON_FUSE_24VAC
        
        # Båda OK
        logger.debug("✅ Säkringar OK: 24VDC=1, 24VAC=1")
        return True, "OK", 0
        
    except Exception as e:
        logger.warning("Fel vid säkrings-kontroll: %s", e)
        return True, "OK", 0  # Fail-safe


def prompt_user_fallback(reason: str) -> str:
    """
    Prompt användare för beslut när automatik inte fungerar
    
    Args:
        reason: Anledning till fallback (t.ex. "API nere", "Sensor fail")
    
    Returns:
        str: Användarens val ("sensor", "force", "abort")
    """
    print(f"\n{'='*60}")
    print(f"⚠️  FALLBACK LÄGE: {reason}")
    print(f"{'='*60}")
    print("\nVälj åtgärd:")
    print("  1) Kör på sensor (om tillgänglig)")
    print("  2) Force Ready (kör oavsett villkor)")
    print("  3) Avbryt (kör inte bevattning)")
    print(f"{'='*60}")
    
    while True:
        try:
            choice = input("Ditt val (1/2/3): ").strip()
            if choice == "1":
                return "sensor"
            elif choice == "2":
                return "force"
            elif choice == "3":
                return "abort"
            else:
                print("Ogiltigt val. Välj 1, 2 eller 3.")
        except (KeyboardInterrupt, EOFError):
            print("\nAvbryter...")
            return "abort"


def write_registers_bulk(client, start_address, values, unit=DEFAULT_MODBUS_UNIT):
    """Write multiple consecutive registers in one operation for better performance."""
    try:
        rr = client.write_registers(start_address, [int(v) for v in values], unit=unit)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            logger.warning("Modbus bulk write error at address %s", start_address)
            return False
        return True
    except Exception as e:
        logger.warning("Modbus bulk write exception: %s", e)
        return False


def write_register(client, address, value, unit=DEFAULT_MODBUS_UNIT):
    try:
        rr = client.write_register(address, int(value), unit=unit)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            logger.warning("Modbus skrivfel address %s", address)
            return False
        return True
    except Exception as e:
        logger.warning("Modbus skrivexception: %s", e)
        return False


def pulse_remote_command(host, port, unit, cmd_reg=MW_REMOTE_CMD, cmd_value=50, pulse_seconds=1, dry_run=False):
    if dry_run:
        logger.info("DRY RUN: skulle pulserat %s -> %s -> 0", cmd_reg, cmd_value)
        return True
    client = open_modbus_client(host, port)
    try:
        if not client.connect():
            logger.warning("Kunde inte ansluta för pulsering.")
            return False
        ok = write_register(client, cmd_reg, cmd_value, unit=unit)
        if not ok:
            client.close()
            return False
        time.sleep(pulse_seconds)
        ok2 = write_register(client, cmd_reg, 0, unit=unit)
        client.close()
        return ok and ok2
    except Exception as e:
        logger.warning("Fel vid pulsering: %s", e)
        try:
            client.close()
        except Exception:
            pass
        return False


def check_pump_safety_from_modbus(
    state: PumpState,
    host: str,
    port: int,
    unit: int
) -> dict:
    """
    Läser sensorer från Modbus och kör pump-safety-check.
    
    Returns:
        {
            "action": str,         # "OK", "STOP_NORMAL", "ALARM_SLANGBROTT", "ALARM_TORRKORNING"
            "alarm": str,          # Beskrivning av larm (None om OK)
            "block_code": int,     # Block reason code
            "diagnostics": dict    # Sensor-värden för loggning
        }
    """
    client = open_modbus_client(host, port)
    
    try:
        if not client.connect():
            logger.warning("Kunde inte ansluta för pump-safety-check")
            return {"action": "OK", "alarm": None, "block_code": 0, "diagnostics": {}}
        
        # Läs sensorer
        pump_reg = client.read_holding_registers(MW_STATUS_PUMP, 1, unit=unit)
        flow_reg = client.read_holding_registers(MW_FLOW_SWITCH, 1, unit=unit)
        pressure_reg = client.read_holding_registers(MW_PRESSURE_SWITCH, 1, unit=unit)
        
        client.close()
        
        if any(r is None or (hasattr(r, 'isError') and r.isError()) 
               for r in [pump_reg, flow_reg, pressure_reg]):
            logger.warning("Kunde inte läsa pump-status från Modbus")
            return {"action": "OK", "alarm": None, "block_code": 0, "diagnostics": {}}
        
        pump_active = pump_reg.registers[0] == 1
        flow_detected = flow_reg.registers[0] == 1
        pressure_ok = pressure_reg.registers[0] == 1
        
        # Beräkna delta_time
        now = time.time()
        if state.last_check is None:
            delta_time = 0.0
        else:
            delta_time = now - state.last_check
        state.last_check = now
        
        # Kör safety-check
        result = check_pump_safety(
            state=state,
            pump_active=pump_active,
            flow_detected=flow_detected,
            pressure_ok=pressure_ok,
            delta_time=delta_time
        )
        
        # Mappa till block reason codes
        block_codes = {
            "ALARM_SLANGBROTT": 11,
            "ALARM_TORRKORNING": 12,
            "STOP_NORMAL": 0,
            "OK": 0
        }
        
        diagnostics = get_diagnostics(state, pump_active, flow_detected, pressure_ok)
        
        return {
            "action": result,
            "alarm": result if result != "OK" else None,
            "block_code": block_codes[result],
            "diagnostics": diagnostics
        }
        
    except Exception as e:
        logger.warning(f"Fel vid pump-safety-check: {e}")
        try:
            client.close()
        except:
            pass
        return {"action": "OK", "alarm": None, "block_code": 0, "diagnostics": {}}


def stop_pump_emergency(host: str, port: int, unit: int, alarm_reason: str, block_code: int):
    """Nödstopp av pump vid kritiskt larm"""
    logger.error(f"🚨 NÖDSTOPP: {alarm_reason}")
    
    client = open_modbus_client(host, port)
    try:
        if client.connect():
            # Stoppa pump
            client.write_register(MW_REMOTE_CMD, 0, unit=unit)
            
            # Skriv block reason
            client.write_register(MW_BLOCK_REASON, block_code, unit=unit)
            
            client.close()
            logger.info(f"Pump stoppad och block reason satt till {block_code}")
        else:
            logger.error("Kunde inte stoppa pump - Modbus-anslutning misslyckades")
    except Exception as e:
        logger.error(f"Fel vid pump-stopp: {e}")
        try:
            client.close()
        except:
            pass


def main_once(args):
    logger.info("=== Bevattningsscript Körning Startad ===")
    
    # === STEG 1: KRITISK SÄKERHETS-KONTROLL - SÄKRINGAR ===
    if not args.simulate and not args.dry_run:
        client = open_modbus_client(args.host, args.port)
        try:
            if client.connect():
                fuses_ok, fuse_reason, block_code = check_power_fuses(client, args.unit)
                client.close()
                
                if not fuses_ok:
                    logger.error("⛔ BEVATTNING BLOCKERAD: %s", fuse_reason)
                    logger.error("   → Ingen bevattning (inklusive Fallback) tillåten")
                    return {
                        "error": fuse_reason,
                        "block_reason": block_code,
                        "wrote": False
                    }
            else:
                logger.warning("Kunde inte ansluta för säkrings-kontroll")
        except Exception as e:
            logger.warning("Fel vid säkrings-kontroll: %s", e)
            try:
                client.close()
            except:
                pass
    
    # === STEG 2: Kontrollera säsong ===
    season_block, season_warning = check_season()
    if season_block:
        logger.error(season_warning)
        logger.error("BEVATTNING AVBRUTEN: Vinterperiod")
        return {
            "error": "Vinterperiod",
            "wrote": False
        }
    if season_warning:
        logger.warning(season_warning)
    
    logger.info("Hämtar väderdata från Open-Meteo...")
    temp, regn = hamta_vader(args.lat, args.lon)
    
    # Hantera fallback om väderdata saknas
    weather_failed = (temp is None or regn is None)
    if weather_failed:
        logger.error("🚨 VÄDERDATA EJ TILLGÄNGLIG: Open-Meteo API nere")
        logger.error("   → Automatik stoppad")
        logger.error("   → Använd '/command/start-fallback' för manuell körning")
        return {
            "error": "Weather API unavailable",
            "wrote": False
        }
    
    # === PUMP SAFETY CHECK (NYT) ===
    global _pump_state
    if not args.simulate and not args.dry_run:
        logger.debug("Kör pump safety check...")
        pump_safety_result = check_pump_safety_from_modbus(
            state=_pump_state,
            host=args.host,
            port=args.port,
            unit=args.unit
        )
        
        # Logga diagnostik
        logger.debug(f"Pump diagnostik: {pump_safety_result['diagnostics']}")
        
        # Hantera kritiska larm
        if pump_safety_result["action"] in ["ALARM_SLANGBROTT", "ALARM_TORRKORNING"]:
            logger.error(f"⛔ PUMP-LARM: {pump_safety_result['alarm']}")
            
            # Stoppa pump
            stop_pump_emergency(
                args.host, 
                args.port, 
                args.unit, 
                pump_safety_result["alarm"],
                pump_safety_result["block_code"]
            )
            
            # Skicka e-post (om konfigurerat)
            try:
                from healthcheck import send_pump_alarm
                send_pump_alarm(pump_safety_result["alarm"], pump_safety_result["diagnostics"])
            except Exception as e:
                logger.warning(f"Kunde inte skicka pump-larm via e-post: {e}")
            
            return {
                "error": pump_safety_result["alarm"],
                "block_reason": pump_safety_result["block_code"],
                "diagnostics": pump_safety_result["diagnostics"],
                "wrote": False
            }
        
        # Hantera normal avslutning (slangvinda)
        elif pump_safety_result["action"] == "STOP_NORMAL":
            logger.info("✅ Slangvinda avslutad normalt - Skriver 0-tider")
            
            # Skriv 0-tider för att signalera "klart"
            client = open_modbus_client(args.host, args.port)
            try:
                if client.connect():
                    client.write_register(MW_TID_CENTER, 0, unit=args.unit)
                    client.write_register(MW_TID_HORN, 0, unit=args.unit)
                    client.close()
                    logger.info("0-tider skrivna till PLC")
            except Exception as e:
                logger.warning(f"Kunde inte skriva 0-tider: {e}")
            
            return {
                "status": "STOP_NORMAL",
                "tid_center": 0,
                "tid_horn": 0,
                "diagnostics": pump_safety_result["diagnostics"],
                "wrote": True
            }

    markfukt = args.simulate_markfukt_value if args.simulate else 30
    
    if args.read_markfukt and not args.simulate:
        logger.info("Läser markfukt från Modbus register %d...", MK_REG_ADDR)
        markfukt_sensor_value = read_markfukt_from_modbus(
            MK_REG_ADDR, host=args.host, port=args.port, unit=args.unit
        )
        if markfukt_sensor_value is not None:
            # TODO: För fullständig spänningsvalidering, läs råvärdet från analog input (%IW0)
            # Nuvarande: MK_REG_ADDR (100) kan innehålla redan konverterat %-värde
            # Om värdet är mycket lågt (< 10%), indikerar det möjligt sensorfel
            if markfukt_sensor_value < 10:
                logger.error("🚨 MARKFUKT-SENSOR FEL: Värde %d%% är ovanligt lågt (möjligt kabelbrott)", markfukt_sensor_value)
                logger.error("   → Automatik stoppad")
                logger.error("   → Använd '/command/start-fallback' för manuell körning")
                return {
                    "error": "Sensor fault (Markfukt < 10%)",
                    "sensor": "moisture",
                    "value": markfukt_sensor_value,
                    "wrote": False
                }
            
            markfukt = markfukt_sensor_value
            logger.info("Markfukt läst från sensor: %d%%", markfukt)
        else:
            logger.error("🚨 MARKFUKT-SENSOR EJ TILLGÄNGLIG")
            logger.error("   → Automatik stoppad")
            logger.error("   → Använd '/command/start-fallback' för manuell körning")
            return {
                "error": "Moisture sensor unavailable",
                "wrote": False
            }
    else:
        logger.info("Använder %s markfukt: %d%%", "simulerad" if args.simulate else "standard", markfukt)

    faktor = 1.0
    anledning = "Normal drift"
    if regn > args.rain_threshold:
        faktor = 0.0
        anledning = f"Regn {regn:.1f}mm > {args.rain_threshold}"
        logger.warning("BEVATTNING BLOCKERAD: %s", anledning)
    elif markfukt >= args.moisture_threshold:
        faktor = 0.0
        anledning = f"Markfukt {markfukt}% >= {args.moisture_threshold}"
        logger.warning("BEVATTNING BLOCKERAD: %s", anledning)
    elif temp < args.temp_min:
        faktor = 0.5
        anledning = f"Kallt ({temp:.1f}C)"
        logger.info("BEVATTNING REDUCERAD: %s", anledning)
    elif regn > 1.0:
        faktor = 0.7
        anledning = f"Litet regn ({regn:.1f}mm)"
        logger.info("BEVATTNING REDUCERAD: %s", anledning)
    else:
        logger.info("BEVATTNING KÖRNING: Normala förhållanden")

    tid_center = int(BASE_TID_CENTER * faktor)
    tid_horn = int(BASE_TID_HORN * faktor)
    
    # Kontrollera zonkonfiguration och anpassa tider
    if HAS_ZONE_CONFIG:
        try:
            zone_config = ZoneConfig()
            enabled_zones = zone_config.get_enabled_zones()
            disabled_zones = zone_config.get_disabled_zones()
            
            if disabled_zones:
                logger.info("📋 Zone configuration loaded: %d enabled, %d disabled", 
                           len(enabled_zones), len(disabled_zones))
                for zone_id in disabled_zones:
                    logger.info("⏭️  Zone %d is disabled by user", zone_id)
            
            # Zoner 1-3 är center, 4-7 är hörn
            center_zones = [1, 2, 3]
            horn_zones = [4, 5, 6, 7]
            
            # Kontrollera om alla center-zoner är inaktiverade
            center_enabled = any(zone_id in enabled_zones for zone_id in center_zones)
            horn_enabled = any(zone_id in enabled_zones for zone_id in horn_zones)
            
            if not center_enabled:
                tid_center = 0
                logger.info("⏭️  All center zones (1-3) disabled, setting tid_center=0")
            
            if not horn_enabled:
                tid_horn = 0
                logger.info("⏭️  All horn zones (4-7) disabled, setting tid_horn=0")
                
        except Exception as e:
            logger.warning("Kunde inte läsa zonkonfiguration: %s, fortsätter utan zonfiltrering", e)

    logger.info("Väder: temp=%.1fC regn24h=%.1fmm markfukt=%s%% => %s => tider %d/%d min",
                temp, regn, markfukt, anledning, tid_center, tid_horn)

    wrote = False
    if not args.dry_run:
        if ModbusTcpClient is None:
            logger.warning("pymodbus saknas — hoppar Modbus-skrivning")
        else:
            logger.info("Skriver data till PLC via Modbus...")
            client = open_modbus_client(args.host, args.port)
            try:
                if client.connect():
                    logger.debug("Modbus-anslutning etablerad till %s:%d", args.host, args.port)
                    # Use bulk write for better performance - write registers in two groups
                    # Group 1: MW20-21 (tid_center, tid_horn)
                    ok1 = write_registers_bulk(client, MW_TID_CENTER, [int(tid_center), int(tid_horn)], unit=args.unit)
                    if ok1:
                        logger.info("Bevattningstider skrivna: Center=%d min, Hörn=%d min", tid_center, tid_horn)
                    # Group 2: MW30-32 (markfukt, regen, temp)
                    ok2 = write_registers_bulk(client, MW_MARKFUKT, 
                                              [int(markfukt), int(regn), int(temp)], 
                                              unit=args.unit)
                    if ok2:
                        logger.info("Miljödata skrivna: Markfukt=%d%%, Regn=%.1fmm, Temp=%.1fC", 
                                  markfukt, regn, temp)
                    client.close()
                    wrote = ok1 and ok2
                    if wrote:
                        logger.info("=== Modbus-skrivning LYCKADES ===")
                    else:
                        logger.error("=== Modbus-skrivning MISSLYCKADES ===")
                else:
                    logger.warning("Kunde inte ansluta till Modbus för skrivning.")
            except Exception as e:
                logger.warning("Fel vid Modbus-skrivning: %s", e)
                try:
                    client.close()
                except Exception:
                    pass
    else:
        logger.info("=== DRY RUN MODE - Ingen Modbus-skrivning utförd ===")

    try:
        os.makedirs(os.path.dirname(LOG_FIL), exist_ok=True)
        with open(LOG_FIL, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             f"temp={temp:.1f}", f"rain24h={regn:.1f}",
                             f"moisture={markfukt}", anledning, tid_center, tid_horn, "written" if wrote else "not_written"])
    except Exception as e:
        logger.warning("Kunde inte skriva loggfil: %s", e)

    if args.auto_start and (tid_center > 0 or tid_horn > 0):
        if args.simulate:
            logger.info("=== SIMULATE MODE: Skulle pulserat Remote_Command (MW10) ===")
        else:
            logger.info("Startar auto-bevattning via Remote_Command puls...")
            ok = pulse_remote_command(args.host, args.port, args.unit, cmd_reg=MW_REMOTE_CMD,
                                      cmd_value=50, pulse_seconds=args.pulse_seconds, dry_run=args.dry_run)
            if ok:
                logger.info("=== AUTO-BEVATTNING STARTAD (Remote_Command pulserad) ===")
            else:
                logger.error("=== AUTO-BEVATTNING MISSLYCKADES (Remote_Command pulsering fel) ===")
    else:
        logger.debug("Ingen auto-start (auto_start=%s, tider %d/%d)", args.auto_start, tid_center, tid_horn)
        if tid_center == 0 and tid_horn == 0:
            logger.info("=== BEVATTNING BLOCKERAD: Tider satta till 0 ===")

    return {
        "temp": temp,
        "rain24h": regn,
        "moisture": markfukt,
        "tid_center": tid_center,
        "tid_horn": tid_horn,
        "wrote": wrote,
        "reason": anledning
    }


def build_argparser():
    p = argparse.ArgumentParser(description="Bevattning controller - Open-Meteo -> Modbus")
    p.add_argument("--host", "-H", default=DEFAULT_MODBUS_HOST, help="Modbus host")
    p.add_argument("--port", "-P", type=int, default=DEFAULT_MODBUS_PORT, help="Modbus port")
    p.add_argument("--unit", "-u", type=int, default=DEFAULT_MODBUS_UNIT, help="Modbus unit id")
    p.add_argument("--lat", default=DEFAULT_LATITUDE, help="Latitude för vädertjänst")
    p.add_argument("--lon", default=DEFAULT_LONGITUDE, help="Longitude för vädertjänst")
    p.add_argument("--loop", action="store_true", help="Kör i loop")
    p.add_argument("--interval", type=int, default=60, help="Intervall i minuter i loop mode")
    p.add_argument("--simulate", action="store_true", help="Simulera, skriv ej Modbus, ingen puls")
    p.add_argument("--simulate-markfukt-value", type=int, default=30, help="Simulerad markfukt (procent)")
    p.add_argument("--read-markfukt", action="store_true", help="Läs markfukt från Modbus addr MK_REG_ADDR")
    p.add_argument("--auto-start", action="store_true", help="Pulsera Remote_Command (MW10) om tider > 0")
    p.add_argument("--pulse-seconds", type=float, default=1.0, help="Sekunder för puls")
    p.add_argument("--dry-run", action="store_true", help="Logga men skriv inte Modbus")
    p.add_argument("--rain-threshold", type=float, default=GRANS_REGN_PROGNOS, help="Regntröskel mm/24h")
    p.add_argument("--moisture-threshold", type=int, default=80, help="Markfuktströskel (procent)")
    p.add_argument("--temp-min", type=float, default=GRANS_TEMP_MIN, help="Temperatur min för reducerad drift")
    p.add_argument("--log-file", default=None, help="Loggfil (om inte angiven används default)")
    p.add_argument("--once", action="store_true", help="Kör endast en gång")
    p.add_argument("--max-retry-delay", type=int, default=300, help="Max retry delay in seconds for exponential backoff")
    return p


def main():
    parser = build_argparser()
    args = parser.parse_args()

    if args.log_file:
        fh = logging.FileHandler(args.log_file)
        fh.setFormatter(_formatter)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)

    try:
        if args.loop and not args.once:
            logger.info("Startar i loop mode, intervall %d minuter.", args.interval)
            consecutive_failures = 0
            while True:
                try:
                    result = main_once(args)
                    # Reset failure count on success
                    if result and isinstance(result, dict) and result.get("wrote"):
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                    
                    # Calculate delay with exponential backoff on failures
                    base_delay = max(10, args.interval * 60)
                    if consecutive_failures > 0:
                        # Exponential backoff: delay * 2^failures, capped at max_retry_delay
                        backoff_delay = min(base_delay * (2 ** (consecutive_failures - 1)), args.max_retry_delay)
                        logger.info("Backing off due to %d consecutive failures, waiting %d seconds", 
                                  consecutive_failures, backoff_delay)
                        time.sleep(backoff_delay)
                    else:
                        time.sleep(base_delay)
                except Exception as e:
                    consecutive_failures += 1
                    logger.exception("Error in loop iteration: %s", e)
                    backoff_delay = min(60 * (2 ** (consecutive_failures - 1)), args.max_retry_delay)
                    logger.info("Retrying after %d seconds", backoff_delay)
                    time.sleep(backoff_delay)
        else:
            main_once(args)
    except KeyboardInterrupt:
        logger.info("Avbröts av användaren.")
    except Exception as e:
        logger.exception("Oväntat fel: %s", e)


if __name__ == "__main__":
    main()
