#!/usr/bin/env python3
"""
Bevattning_controller.py (uppdaterad)
- Hämtar väder från Open-Meteo, valfritt markfukt via Modbus.
- Skriver temp/regn/markfukt/tider till PLC via Modbus.
- Pulserar Remote_Command (MW10) vid behov.
- Fallback och begränsning av rimliga värden.
- Kan köras en gång eller i loop.
"""
from datetime import datetime, timedelta
import time
import os
import csv
import argparse
import logging
import requests

try:
    from pymodbus.client import ModbusTcpClient
except Exception:
    try:
        from pymodbus.client.sync import ModbusTcpClient
    except Exception:
        ModbusTcpClient = None

DEFAULT_MODBUS_HOST = "127.0.0.1"
DEFAULT_MODBUS_PORT = 502
DEFAULT_MODBUS_UNIT = 1

LOG_FIL = os.path.join(os.path.expanduser("~"), "bevattning_log.csv")
DEFAULT_LATITUDE = "56.10"
DEFAULT_LONGITUDE = "14.45"

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

MK_REG_ADDR = 100  # exempelfält för extern markfukt-läsning

# Weather cache to avoid excessive API calls in loop mode
_weather_cache = {"data": None, "timestamp": None, "cache_duration": 600}  # 10 minutes cache

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
        # Open-Meteo API - gratis, inget API-nyckel behövs
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&hourly=precipitation&timezone=auto&forecast_days=2"
        headers = {"User-Agent": "BevattningController/1.2"}
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        data = r.json()

        # Hämta aktuell temperatur
        temp_nu = data.get("current", {}).get("temperature_2m")
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


def main_once(args):
    logger.info("Startar bevattningsscript")
    temp, regn = hamta_vader(args.lat, args.lon)
    if temp is None:
        temp = 15.0
        regn = 0.0

    markfukt = args.simulate_markfukt_value if args.simulate else 30
    if args.read_markfukt and not args.simulate:
        mf = read_markfukt_from_modbus(MK_REG_ADDR, host=args.host, port=args.port, unit=args.unit)
        if mf is not None:
            markfukt = mf
        else:
            logger.info("Använder simulerad markfukt pga läsfel")

    faktor = 1.0
    anledning = "Normal drift"
    if regn is not None and regn > args.rain_threshold:
        faktor = 0.0
        anledning = f"Regn {regn:.1f}mm > {args.rain_threshold}"
    elif markfukt >= args.moisture_threshold:
        faktor = 0.0
        anledning = f"Markfukt {markfukt}% >= {args.moisture_threshold}"
    elif temp < args.temp_min:
        faktor = 0.5
        anledning = f"Kallt ({temp:.1f}C)"
    elif regn is not None and regn > 1.0:
        faktor = 0.7
        anledning = f"Litet regn ({regn:.1f}mm)"

    tid_center = int(BASE_TID_CENTER * faktor)
    tid_horn = int(BASE_TID_HORN * faktor)

    logger.info("Väder: temp=%.1fC regn24h=%.1fmm markfukt=%s%% => %s => tider %d/%d min",
                temp, (regn if regn is not None else 0.0), markfukt, anledning, tid_center, tid_horn)

    wrote = False
    if not args.dry_run:
        if ModbusTcpClient is None:
            logger.warning("pymodbus saknas — hoppar Modbus-skrivning")
        else:
            client = open_modbus_client(args.host, args.port)
            try:
                if client.connect():
                    # Use bulk write for better performance - write 5 consecutive registers (MW30-MW34)
                    # MW30=markfukt, MW31=regen, MW32=temp, MW33=tid_center (non-standard but efficient)
                    # Actually MW20=tid_center, MW21=tid_horn, so we'll do two bulk writes
                    # First: MW20-21 (tider)
                    ok1 = write_registers_bulk(client, MW_TID_CENTER, [int(tid_center), int(tid_horn)], unit=args.unit)
                    # Second: MW30-32 (markfukt, regen, temp)
                    ok2 = write_registers_bulk(client, MW_MARKFUKT, 
                                              [int(markfukt), int(regn if regn is not None else 0), int(temp)], 
                                              unit=args.unit)
                    client.close()
                    wrote = ok1 and ok2
                else:
                    logger.warning("Kunde inte ansluta till Modbus för skrivning.")
            except Exception as e:
                logger.warning("Fel vid Modbus-skrivning: %s", e)
                try:
                    client.close()
                except Exception:
                    pass
    else:
        logger.info("DRY RUN - ingen Modbus-skrivning.")

    try:
        os.makedirs(os.path.dirname(LOG_FIL), exist_ok=True)
        with open(LOG_FIL, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             f"temp={temp:.1f}", f"rain24h={(regn if regn is not None else 0.0):.1f}",
                             f"moisture={markfukt}", anledning, tid_center, tid_horn, "written" if wrote else "not_written"])
    except Exception as e:
        logger.warning("Kunde inte skriva loggfil: %s", e)

    if args.auto_start and (tid_center > 0 or tid_horn > 0):
        if args.simulate:
            logger.info("SIMULATE: Skulle pulserat Remote_Command (MW10).")
        else:
            ok = pulse_remote_command(args.host, args.port, args.unit, cmd_reg=MW_REMOTE_CMD,
                                      cmd_value=50, pulse_seconds=args.pulse_seconds, dry_run=args.dry_run)
            if ok:
                logger.info("Remote_Command pulserad.")
            else:
                logger.warning("Remote_Command pulsering misslyckades.")
    else:
        logger.debug("Ingen auto-start (auto_start=%s, tider %d/%d)", args.auto_start, tid_center, tid_horn)

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
                    if result and result.get("wrote"):
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