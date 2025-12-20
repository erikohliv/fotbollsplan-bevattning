import logging
import os
import time
from typing import Optional
from contextlib import contextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
import requests

try:
    from pymodbus.client import ModbusTcpClient
except Exception:
    try:
        from pymodbus.client.sync import ModbusTcpClient
    except Exception:
        ModbusTcpClient = None

load_dotenv()

API_LOGGER_NAME = "bevattning.api"


def _setup_logger() -> logging.Logger:
    log = logging.getLogger(API_LOGGER_NAME)
    root_logger = logging.getLogger()
    if not log.handlers and not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    return log


logger = _setup_logger()

USER_MODBUS_ERROR = "PLC-kommunikation misslyckades. Försök igen eller kontakta drift."

API_KEY = os.getenv("API_KEY", "change-me")
MODBUS_HOST = os.getenv("MODBUS_HOST", "127.0.0.1")
MODBUS_PORT = int(os.getenv("MODBUS_PORT", "502"))
MODBUS_UNIT = int(os.getenv("MODBUS_UNIT", "1"))
MODBUS_TIMEOUT = int(os.getenv("MODBUS_TIMEOUT", "3"))

MW_REMOTE_CMD = 10
MW_TID_CENTER = 20
MW_TID_HORN = 21
MW_MARKFUKT = 30
MW_REGEN24 = 31
MW_TEMP = 32
MW_PRESSURE = 33            # Tryckgivare värde (0-100%)
MW_AUTO_OVERRIDE = 34       # AutoOverride (flyttad från 33)
MW_REGEN_THRESHOLD = 35     # Regntröskel i mm (default 5) (flyttad från 34)
MW_MOISTURE_THRESHOLD = 36  # Markfukttröskel i % (default 80) (flyttad från 35)
MW_STATUS_ZONE = 50
MW_STATUS_PUMP = 51
MW_STATUS_STEG = 52
MW_SELECTED_ZONE = 53
MW_FLOW_SWITCH = 55         # Flödesvakt status (0=ingen flöde, 1=flöde OK)
MW_MODE_OVERRIDE = 60
MW_MANUAL_START = 61
MW_SET_SELECTED = 63
MW_MENU_BUTTONS = 64        # Menu buttons bitmask (bit0=Left, bit1=Right, bit2=OK, bit3=Back)
MW_MANUAL_TIME = 65         # Manual runtime in minutes (1-240)
MW_SPECIAL_MODE = 66        # Special mode trigger: 0=none, 1=Test, 2=Blow (PLC clears)
MW_HEARTBEAT = 70
MW_HEARTBEAT_CNT = 71
MW_EVENTMASK = 72
MW_BLOCK_REASON = 73
MW_TEST_MODE = 80           # Test mode aktivering (1=aktiv, 0=inaktiv)
MW_TEST_ZONE_RESULT = 81    # Test resultat för aktuell zon (bitmask för zoner 1-7)
MW_ERROR_RESET = 82         # Error reset trigger (skriv 1 för att nollställa fel)
MW_MODE = 100               # Mode switch: 0=Neutral, 1=Lokalt läge, 2=Fjärrläge

# Säkerhetströsklar för tryck/flöde
PRESSURE_LOW_THRESHOLD = 20       # % - lågt tryck när flöde detekteras
PRESSURE_HIGH_THRESHOLD = 90      # % - nära maxtryck utan flöde indikerar blockering

# Zone constants
MIN_ZONE = 1
MAX_ZONE = 7
# Indicates that block_reason could not be read after reset
BLOCK_REASON_UNKNOWN = -1

app = FastAPI(title="Bevattning API", version="0.3")
security = HTTPBasic()

# Import user management functionality
try:
    from user_management import SuperAdminManager, UserManager
    user_manager = UserManager()
    superadmin_manager = SuperAdminManager()
except ImportError:
    logger.warning("user_management module not available - user management endpoints will be disabled")
    user_manager = None
    superadmin_manager = None


def require_key(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def require_superadmin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify superadmin credentials using HTTP Basic Authentication."""
    if superadmin_manager is None:
        raise HTTPException(
            status_code=503,
            detail="User management not available - missing dependencies"
        )
    
    if not superadmin_manager.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Superadmin not configured - run setup.py first"
        )
    
    # Verify username is 'superadmin' and password is correct
    if credentials.username != "superadmin":
        raise HTTPException(
            status_code=401,
            detail="Invalid superadmin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not superadmin_manager.verify_password(credentials.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid superadmin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


def validate_zone(value: int) -> int:
    if value < 1 or value > 7:
        raise HTTPException(status_code=400, detail="zone must be 1..7")
    return value


def validate_minutes(value: int) -> int:
    if value < 1 or value > 240:
        raise HTTPException(status_code=400, detail="minutes must be 1..240")
    return value


def clamp_tid_center(value: int) -> int:
    """Clamp tid_center value to valid range 0-240"""
    return max(0, min(240, value))


def clamp_tid_horn(value: int) -> int:
    """Clamp tid_horn value to valid range 0-240"""
    return max(0, min(240, value))


def clamp_markfukt(value: int) -> int:
    """Clamp markfukt value to valid range 0-100"""
    return max(0, min(100, value))


def clamp_regen(value: int) -> int:
    """Clamp regen24 value to valid range 0-500"""
    return max(0, min(500, value))


def clamp_temp(value: int) -> int:
    """Clamp temperature value to valid range -30 to 50"""
    return max(-30, min(50, value))


def _modbus_has_error(rr) -> bool:
    return rr is None or (hasattr(rr, "isError") and rr.isError())


def _raise_modbus_error(context: str):
    logger.warning(
        "Modbusfel: %s (host=%s port=%s unit=%s)",
        context,
        MODBUS_HOST,
        MODBUS_PORT,
        MODBUS_UNIT,
    )
    raise HTTPException(status_code=502, detail=USER_MODBUS_ERROR)


def _ensure_modbus_ok(rr, context: str):
    if _modbus_has_error(rr):
        _raise_modbus_error(context)


def mb_client():
    if ModbusTcpClient is None:
        raise HTTPException(status_code=500, detail="pymodbus not installed")
    return ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT, timeout=MODBUS_TIMEOUT)


@contextmanager
def get_modbus_connection():
    """Context manager for Modbus connections to ensure proper cleanup."""
    client = mb_client()
    try:
        if not client.connect():
            _raise_modbus_error("connect")
        logger.debug("Modbusanslutning etablerad")
        yield client
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Modbus-undantag: %s", exc)
        raise HTTPException(status_code=502, detail=USER_MODBUS_ERROR) from exc
    finally:
        try:
            client.close()
        except Exception:
            pass


def read_regs(address, count=1):
    with get_modbus_connection() as client:
        rr = client.read_holding_registers(address, count, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, f"read_holding_registers addr={address} count={count}")
        logger.debug("Modbus read addr=%s count=%s -> %s", address, count, getattr(rr, "registers", []))
        return rr.registers


def write_reg(address, value):
    with get_modbus_connection() as client:
        rr = client.write_register(address, int(value), unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, f"write_register addr={address} value={value}")
        logger.debug("Modbus write addr=%s value=%s", address, value)
        return True


def write_regs_bulk(start_address, values):
    """Write multiple registers at once for better performance."""
    with get_modbus_connection() as client:
        rr = client.write_registers(start_address, [int(v) for v in values], unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, f"write_registers start={start_address} values={values}")
        logger.debug("Modbus bulk write start=%s values=%s", start_address, values)
        return True


class ManualCommand(BaseModel):
    zone: int
    # Note: minutes parameter removed - manual mode now uses auto mode times 
    # (Set_Tid_Center for zones 1-3 [MW20], Set_Tid_Horn for zones 4-7 [MW21])
    pulse_seconds: float = 1.0

class SetZone(BaseModel):
    zone: int

class SetManualTime(BaseModel):
    minutes: int


class ConfigUpdate(BaseModel):
    tid_center: Optional[int] = None
    tid_horn: Optional[int] = None
    markfukt: Optional[int] = None
    regen24: Optional[int] = None
    temp_c: Optional[int] = None
    manual_time: Optional[int] = None  # DEPRECATED - kept for backward compatibility
    mode_override: Optional[int] = None  # 1=Auto, 0=Manual


class TestZoneCommand(BaseModel):
    """
    Command för att testa en specifik zon eller alla zoner.
    OBSERVERA: Test av alla zoner tar flera minuter och blockerar API under tiden.
    Rekommenderas att köras när systemet inte används aktivt.
    """
    zone: Optional[int] = None  # Om None, testa alla zoner sekventiellt
    duration_seconds: int = 60  # Testlängd per zon (default 60 sekunder)
    all_zones_confirmed: bool = False  # Säkerhetskontroll för test av alla zoner


@app.get("/status")
def status(x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    # Read registers in two groups to avoid reading undefined intermediate registers.
    # According to the PLC register map, MW54-59, MW62, MW65-69 are not defined.
    # Reading only defined registers prevents potential issues with non-existent or 
    # side-effect registers while still being more efficient than the original implementation.
    # Group 1: MW50-53 (zone, pump, steg, selected_zone)
    # Group 2: MW70-73 (heartbeat data)
    # Group 3: MW_MODE (mode switch status)
    with get_modbus_connection() as client:
        rr1 = client.read_holding_registers(MW_STATUS_ZONE, 4, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr1, "read status registers MW50-53")
        rr2 = client.read_holding_registers(MW_HEARTBEAT, 4, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr2, "read heartbeat registers MW70-73")
        rr3 = client.read_holding_registers(MW_MODE, 1, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr3, f"read mode register MW{MW_MODE}")
        rr_pressure = client.read_holding_registers(MW_PRESSURE, 1, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr_pressure, f"read pressure register MW{MW_PRESSURE}")
        rr_flow = client.read_holding_registers(MW_FLOW_SWITCH, 1, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr_flow, f"read flow switch register MW{MW_FLOW_SWITCH}")
    
    mode_value = rr3.registers[0]
    mode_text = {
        0: "Inget läge valt",
        1: "Lokalt läge aktivt",
        2: "Fjärrläge aktivt"
    }
    pump_on = rr1.registers[1] == 1
    pressure_value = int(rr_pressure.registers[0])
    flow_ok = rr_flow.registers[0] == 1
    blockering = pump_on and (not flow_ok) and pressure_value >= PRESSURE_HIGH_THRESHOLD
    torrkorning = pump_on and (not flow_ok) and not blockering
    safety_flags = {
        "slangbrott": pump_on and flow_ok and pressure_value < PRESSURE_LOW_THRESHOLD,
        "torrkorning": torrkorning,
        "givarkontroll": (not pump_on) and pressure_value >= PRESSURE_HIGH_THRESHOLD,
        "blockering": blockering,
    }
    
    return {
        "zone": rr1.registers[0],
        "pump_on": pump_on,
        "steg": rr1.registers[2],
        "selected_zone": rr1.registers[3],
        "heartbeat_bit": rr2.registers[0],
        "heartbeat_count": rr2.registers[1],
        "eventmask": rr2.registers[2],
        "block_reason": rr2.registers[3],
        "mode": mode_value,
        "mode_text": mode_text.get(mode_value, f"Okänt läge {mode_value}"),
        "pressure": pressure_value,
        "flow_ok": flow_ok,
        "safety": safety_flags,
        "timestamp": int(time.time())
    }


def _pulse_remote_command(value: int, pulse_seconds: float = 1.0):
    """Helper function to pulse Remote_Command register"""
    with get_modbus_connection() as client:
        rr = client.write_register(MW_REMOTE_CMD, value, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, f"pulse start remote_command value={value}")
        time.sleep(pulse_seconds)
        rr = client.write_register(MW_REMOTE_CMD, 0, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, "pulse stop remote_command")


@app.post("/command/start-auto")
def start_auto(x_api_key: Optional[str] = Header(None), pulse_seconds: float = 1.0):
    require_key(x_api_key)
    logger.info("[USER_ACTION] Auto-program startas - timestamp=%s", int(time.time()))
    _pulse_remote_command(50, pulse_seconds)
    logger.info("[USER_ACTION] Auto-program startkommando skickat")
    return {"ok": True}


@app.post("/command/start-night-program")
def start_night_program(x_api_key: Optional[str] = Header(None), pulse_seconds: float = 1.0):
    """
    Starta natt-program (kör alla zoner som auto-mode).
    Detta tvingar fram en "natt körning" genom att aktivera auto-mode.
    """
    require_key(x_api_key)
    logger.info("[USER_ACTION] Natt-program startas via API - timestamp=%s", int(time.time()))
    _pulse_remote_command(50, pulse_seconds)
    logger.info("[USER_ACTION] Natt-program startkommando skickat - alla zoner kommer köras")
    return {"ok": True, "message": "Natt-program startat (alla zoner)"}


@app.post("/command/manual")
def start_manual(cmd: ManualCommand, x_api_key: Optional[str] = Header(None)):
    """
    Start manual irrigation for selected zone.
    Manual mode runs only the selected zone (not a full sequence),
    using the same times as auto mode (Set_Tid_Center for zones 1-3, Set_Tid_Horn for zones 4-7).
    """
    require_key(x_api_key)
    zone = validate_zone(cmd.zone)
    logger.info("[USER_ACTION] Manuell körning initieras - zon=%s timestamp=%s", zone, int(time.time()))
    # Write selected zone and pulse manual start
    with get_modbus_connection() as client:
        rr = client.write_register(MW_SET_SELECTED, zone, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, f"set selected zone {zone}")
        # Pulse manual start
        rr = client.write_register(MW_MANUAL_START, 1, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, f"manual start for zone {zone}")
    logger.info("[USER_ACTION] Manuell körning startad - zon=%s", zone)
    return {"ok": True, "zone": zone, "note": "Manual mode runs only the selected zone using auto times"}


@app.post("/command/set-zone")
def set_zone(cmd: SetZone, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    zone = validate_zone(cmd.zone)
    logger.info("Zon %s vald manuellt", zone)
    write_reg(MW_SET_SELECTED, zone)
    return {"ok": True, "zone": zone}


@app.post("/command/set-manual-time")
def set_manual_time(cmd: SetManualTime, x_api_key: Optional[str] = Header(None)):
    """
    DEPRECATED: Manual time setting is no longer used.
    Manual mode now uses the same times as auto mode (Set_Tid_Center/Set_Tid_Horn).
    This endpoint is kept for backward compatibility but has no effect.
    """
    require_key(x_api_key)
    minutes = validate_minutes(cmd.minutes)
    # Endpoint kept for backward compatibility but does nothing
    return {"ok": True, "minutes": minutes, "note": "DEPRECATED - manual mode now uses auto times"}


@app.post("/command/stop")
def stop(x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    logger.info("[USER_ACTION] Stopp-kommando mottaget - timestamp=%s", int(time.time()))
    # Reuse connection for multiple writes
    with get_modbus_connection() as client:
        rr = client.write_register(MW_REMOTE_CMD, 0, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, "stop remote command")
        rr = client.write_register(MW_MODE_OVERRIDE, 0, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, "reset mode override")
    logger.info("[USER_ACTION] Stopp-kommando verkställt - pump och sekvens stoppad")
    return {"ok": True}


@app.post("/config")
def config(cfg: ConfigUpdate, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    logger.info("Konfiguration uppdateras: %s", cfg.model_dump(exclude_none=True))
    # Reuse connection for multiple writes - connection already optimized
    with get_modbus_connection() as client:
        # Optimize: Use bulk write for consecutive registers MW20-21 when both provided
        if cfg.tid_center is not None and cfg.tid_horn is not None:
            values = [clamp_tid_center(cfg.tid_center), clamp_tid_horn(cfg.tid_horn)]
            rr = client.write_registers(MW_TID_CENTER, values, unit=MODBUS_UNIT)
            _ensure_modbus_ok(rr, f"write tid_center/tid_horn values={values}")
        else:
            if cfg.tid_center is not None:
                rr = client.write_register(MW_TID_CENTER, clamp_tid_center(cfg.tid_center), unit=MODBUS_UNIT)
                _ensure_modbus_ok(rr, f"write tid_center value={cfg.tid_center}")
            if cfg.tid_horn is not None:
                rr = client.write_register(MW_TID_HORN, clamp_tid_horn(cfg.tid_horn), unit=MODBUS_UNIT)
                _ensure_modbus_ok(rr, f"write tid_horn value={cfg.tid_horn}")
        
        # Optimize: Use bulk write for consecutive registers MW30-32 when all three provided
        if cfg.markfukt is not None and cfg.regen24 is not None and cfg.temp_c is not None:
            values = [clamp_markfukt(cfg.markfukt), 
                     clamp_regen(cfg.regen24), 
                     clamp_temp(cfg.temp_c)]
            rr = client.write_registers(MW_MARKFUKT, values, unit=MODBUS_UNIT)
            _ensure_modbus_ok(rr, f"write markfukt/regen24/temp_c values={values}")
        else:
            if cfg.markfukt is not None:
                rr = client.write_register(MW_MARKFUKT, clamp_markfukt(cfg.markfukt), unit=MODBUS_UNIT)
                _ensure_modbus_ok(rr, f"write markfukt value={cfg.markfukt}")
            if cfg.regen24 is not None:
                rr = client.write_register(MW_REGEN24, clamp_regen(cfg.regen24), unit=MODBUS_UNIT)
                _ensure_modbus_ok(rr, f"write regen24 value={cfg.regen24}")
            if cfg.temp_c is not None:
                rr = client.write_register(MW_TEMP, clamp_temp(cfg.temp_c), unit=MODBUS_UNIT)
                _ensure_modbus_ok(rr, f"write temp_c value={cfg.temp_c}")
        
        # manual_time is deprecated - kept for backward compatibility but does nothing
        if cfg.manual_time is not None:
            # No-op for backward compatibility
            pass
        if cfg.mode_override is not None:
            rr = client.write_register(MW_MODE_OVERRIDE, 1 if cfg.mode_override == 1 else 0, unit=MODBUS_UNIT)
            _ensure_modbus_ok(rr, f"write mode_override value={cfg.mode_override}")
    return {"ok": True}


@app.post("/menu/test-bevattning")
def test_bevattning(cmd: TestZoneCommand, x_api_key: Optional[str] = Header(None)):
    """
    Test Bevattning - Pre-season zone check.
    Testar varje zon i 1 minut (eller angivet antal sekunder) för att verifiera funktion.
    
    VARNING: Denna operation blockerar API under testperioden.
    Test av alla zoner kräver all_zones_confirmed=true som säkerhetskontroll.
    Errors in individual zones are logged and testing continues for remaining zones to provide complete results.
    """
    require_key(x_api_key)
    
    zones_to_test = [cmd.zone] if cmd.zone is not None else list(range(MIN_ZONE, MAX_ZONE + 1))
    
    # Säkerhetskontroll för test av alla zoner
    if cmd.zone is None and not cmd.all_zones_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Test av alla zoner kräver all_zones_confirmed=true (detta tar flera minuter)"
        )
    
    test_results = {}
    
    with get_modbus_connection() as client:
        # Log and continue with remaining zones even if one zone fails
        logger.info("Startar zontest: zones=%s duration=%ss", zones_to_test, cmd.duration_seconds)
        # Aktivera test mode
        rr = client.write_register(MW_TEST_MODE, 1, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, "enable test mode")
        
        for zone in zones_to_test:
            if zone < MIN_ZONE or zone > MAX_ZONE:
                continue
                
            # Välj zon
            rr = client.write_register(MW_SET_SELECTED, zone, unit=MODBUS_UNIT)
            # Don't abort entire test on individual failures; log and continue to next zone
            if _modbus_has_error(rr):
                logger.warning("Misslyckades välja zon %s under test", zone)
                test_results[f"zone_{zone}"] = "failed_zone_select"
                continue
            
            # Starta manuell körning
            rr = client.write_register(MW_MANUAL_START, 1, unit=MODBUS_UNIT)
            if _modbus_has_error(rr):
                logger.warning("Misslyckades starta test för zon %s", zone)
                test_results[f"zone_{zone}"] = "failed_start"
                continue
            
            # Vänta för testperioden
            # NOTE: This blocks the API thread. Consider running tests via separate process/service
            # for production use to avoid blocking concurrent API requests.
            time.sleep(cmd.duration_seconds)
            
            # Stoppa
            rr = client.write_register(MW_REMOTE_CMD, 0, unit=MODBUS_UNIT)
            if _modbus_has_error(rr):
                logger.warning("Misslyckades stoppa test för zon %s", zone)
                test_results[f"zone_{zone}"] = "failed_stop"
                continue
                
            # Markera som testad (sätt bit i test result register)
            current_result = client.read_holding_registers(MW_TEST_ZONE_RESULT, 1, unit=MODBUS_UNIT)
            if not _modbus_has_error(current_result):
                result_value = current_result.registers[0] | (1 << (zone - 1))
                client.write_register(MW_TEST_ZONE_RESULT, result_value, unit=MODBUS_UNIT)
                test_results[f"zone_{zone}"] = "success"
            else:
                test_results[f"zone_{zone}"] = "failed_log"
            
            # Kort paus mellan zoner för att undvika att överbelasta systemet
            if len(zones_to_test) > 1:
                time.sleep(2)
        
        # Avaktivera test mode
        rr = client.write_register(MW_TEST_MODE, 0, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, "disable test mode")
    
    return {
        "ok": True,
        "test_results": test_results,
        "zones_tested": zones_to_test,
        "duration_per_zone": cmd.duration_seconds
    }


@app.post("/menu/lagesval")
def lagesval(mode: int, x_api_key: Optional[str] = Header(None)):
    """
    Lägesval - Toggle mellan Manual och Auto mode.
    mode: 1=Auto, 0=Manual
    """
    require_key(x_api_key)
    
    if mode not in [0, 1]:
        raise HTTPException(status_code=400, detail="mode must be 0 (Manual) or 1 (Auto)")
    
    with get_modbus_connection() as client:
        # Kontrollera block reason - vissa tillstånd kan förhindra lägesändring
        block_check = client.read_holding_registers(MW_BLOCK_REASON, 1, unit=MODBUS_UNIT)
        _ensure_modbus_ok(block_check, "read block status")
        
        block_reason = block_check.registers[0]
        if block_reason == 4:  # E-stop
            raise HTTPException(status_code=400, detail="Cannot change mode: E-stop active")
        
        # Sätt mode
        rr = client.write_register(MW_MODE_OVERRIDE, mode, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, f"write mode {mode}")
    
    logger.info("Lägesval ändrat till %s", "Auto" if mode == 1 else "Manual")
    return {
        "ok": True,
        "mode": "Auto" if mode == 1 else "Manual",
        "mode_value": mode
    }


@app.get("/menu/felsökning")
def felsokning(x_api_key: Optional[str] = Header(None)):
    """
    Felsökning - Hämta detaljerad felstatus och loggning.
    """
    require_key(x_api_key)
    
    with get_modbus_connection() as client:
        # Läs alla relevanta statusregister
        status_regs = client.read_holding_registers(MW_STATUS_ZONE, 4, unit=MODBUS_UNIT)
        heartbeat_regs = client.read_holding_registers(MW_HEARTBEAT, 4, unit=MODBUS_UNIT)
        
        _ensure_modbus_ok(status_regs, "read felsökning status registers")
        _ensure_modbus_ok(heartbeat_regs, "read felsökning heartbeat registers")
        
        block_reason = heartbeat_regs.registers[3]
        eventmask = heartbeat_regs.registers[2]
        
        # Tolka block reason
        block_reasons = {
            0: "OK - Inget fel",
            1: "Regn över tröskel",
            2: "Markfukt över tröskel",
            3: "Anti-kollision / Pump upptagen",
            4: "E-stop aktiv"
        }
        
        # Tolka eventmask
        events = {
            "e_stop": bool(eventmask & 0x01),
            "moisture_rain_block": bool(eventmask & 0x02),
            "sequence_active": bool(eventmask & 0x04),
            "anti_collision": bool(eventmask & 0x08),
            "auto_override": bool(eventmask & 0x10)
        }
        
        return {
            "ok": True,
            "current_zone": status_regs.registers[0],
            "pump_on": status_regs.registers[1] == 1,
            "steg": status_regs.registers[2],
            "selected_zone": status_regs.registers[3],
            "block_reason": block_reason,
            "block_reason_text": block_reasons.get(block_reason, f"Okänd kod {block_reason}"),
            "events": events,
            "heartbeat_count": heartbeat_regs.registers[1],
            "timestamp": int(time.time())
        }


@app.post("/menu/reset-error")
def reset_error(x_api_key: Optional[str] = Header(None)):
    """
    Reset Error - Nollställ pump-fel och zonlogik.
    Pulserar ERROR_RESET registret för att återställa PLC-fel.
    """
    require_key(x_api_key)
    
    with get_modbus_connection() as client:
        logger.info("Återställer felstatus via API")
        # Pulsera error reset
        rr = client.write_register(MW_ERROR_RESET, 1, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, "error reset on")
        
        # Kort paus för att PLC ska hinna processa reset
        time.sleep(0.5)
        
        rr = client.write_register(MW_ERROR_RESET, 0, unit=MODBUS_UNIT)
        _ensure_modbus_ok(rr, "error reset off")
        
        # Läs status efter reset
        block_check = client.read_holding_registers(MW_BLOCK_REASON, 1, unit=MODBUS_UNIT)
        if _modbus_has_error(block_check):
            new_block_reason = BLOCK_REASON_UNKNOWN
        else:
            new_block_reason = block_check.registers[0]
    
    return {
        "ok": True,
        "reset_performed": True,
        "new_block_reason": new_block_reason,
        "message": "Error reset performed successfully"
    }


@app.post("/set-mode/{mode}")
def set_mode(mode: int, x_api_key: Optional[str] = Header(None)):
    """
    Ställ in läge via fjärrstyrning eller fysisk switch.
    Mode-värden:
      1 = Lokalt läge
      2 = Fjärrläge
      0 = Neutral (behåll nuvarande läge)
    
    Fysisk switch skriver värdet och återgår automatiskt till 0.
    API kan också användas för att ställa läget.
    """
    require_key(x_api_key)
    
    if mode not in [0, 1, 2]:
        raise HTTPException(
            status_code=400, 
            detail="mode must be 0 (Neutral), 1 (Lokalt läge), or 2 (Fjärrläge)"
        )
    
    logger.info("Ställer läge till %s (0=Neutral, 1=Lokalt, 2=Fjärr)", mode)
    write_reg(MW_MODE, mode)
    
    mode_text = {
        0: "Neutral (ingen ändring)",
        1: "Lokalt läge aktivt",
        2: "Fjärrläge aktivt"
    }
    
    return {
        "ok": True,
        "mode": mode,
        "mode_text": mode_text[mode]
    }


@app.get("/", response_class=HTMLResponse)
def render_control_panel_ui():
    return """
<!doctype html>
<html>
<head>
<title>Bevattning</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
.container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
h2 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
.section { margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 4px; }
.section h3 { margin-top: 0; color: #555; }
.status { background: #e8f5e9; padding: 10px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; }
.controls { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
button { 
  padding: 10px 20px; 
  background: #4CAF50; 
  color: white; 
  border: none; 
  border-radius: 4px; 
  cursor: pointer; 
  font-size: 14px;
}
button:hover { background: #45a049; }
button:disabled { background: #ccc; cursor: not-allowed; }
button.danger { background: #f44336; }
button.danger:hover { background: #da190b; }
button.night { background: #2196F3; }
button.night:hover { background: #0b7dda; }
input, select { 
  padding: 8px; 
  border: 1px solid #ddd; 
  border-radius: 4px; 
  font-size: 14px;
}
label { font-weight: bold; margin-right: 5px; }
.message { 
  padding: 10px; 
  margin: 10px 0; 
  border-radius: 4px; 
  display: none;
}
.message.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.message.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
</style>
</head>
<body>
<div class="container">
  <h2>Bevattning Styrning</h2>
  
  <div class="section">
    <h3>Status</h3>
    <div id="status" class="status">Laddar...</div>
  </div>
  
  <div class="section">
    <h3>Manuell Styrning - Enskild Zon</h3>
    <div class="controls">
      <label>Zon:</label>
      <select id="zone">
        <option value="1">Zon 1</option>
        <option value="2">Zon 2</option>
        <option value="3">Zon 3</option>
        <option value="4">Zon 4</option>
        <option value="5">Zon 5</option>
        <option value="6">Zon 6</option>
        <option value="7">Zon 7</option>
      </select>
      
      <button onclick="startManual()">Starta Zon</button>
    </div>
    <p style="font-size: 12px; color: #666; margin-top: 10px;">
      Använder automatiska tider: Center-zoner (1-3) och Hörn-zoner (4-7) enligt konfiguration.
    </p>
  </div>
  
  <div class="section">
    <h3>Natt-program (Alla Zoner)</h3>
    <div class="controls">
      <button class="night" onclick="startNightProgram()">Starta Natt-program</button>
      <span style="margin-left: 10px; color: #666;">Kör alla zoner enligt konfigurerade tider</span>
    </div>
  </div>
  
  <div class="section">
    <h3>Auto-program</h3>
    <div class="controls">
      <button onclick="startAuto()">Starta Auto</button>
      <button class="danger" onclick="stopAll()">Stoppa</button>
    </div>
  </div>
  
  <div class="section">
    <h3>Meny-system</h3>
    
    <div style="margin-bottom: 15px;">
      <h4 style="margin: 10px 0 5px 0; color: #666;">Test Bevattning (Försäsongskontroll)</h4>
      <div class="controls">
        <button onclick="testAllZones()">Testa Alla Zoner (1 min/zon)</button>
        <button onclick="testSingleZone()">Testa Enskild Zon</button>
      </div>
      <p style="font-size: 12px; color: #666; margin-top: 5px;">
        Testar varje zon i 1 minut för att verifiera funktion innan säsongstart.
      </p>
    </div>
    
    <div style="margin-bottom: 15px;">
      <h4 style="margin: 10px 0 5px 0; color: #666;">Lägesval</h4>
      <div class="controls">
        <button onclick="setMode(1)">Auto-läge</button>
        <button onclick="setMode(0)">Manuellt läge</button>
      </div>
      <p style="font-size: 12px; color: #666; margin-top: 5px;">
        Växla mellan automatisk och manuell drift. E-stop blockerar lägesändring.
      </p>
    </div>
    
    <div style="margin-bottom: 15px;">
      <h4 style="margin: 10px 0 5px 0; color: #666;">Lokal/Fjärr-styrning</h4>
      <div class="controls">
        <button onclick="setSwitchMode(1)">Lokalt läge</button>
        <button onclick="setSwitchMode(2)">Fjärrläge</button>
        <button onclick="setSwitchMode(0)">Neutral</button>
      </div>
      <p style="font-size: 12px; color: #666; margin-top: 5px;">
        Växla mellan lokalt (fysisk styrning) och fjärrstyrning. Neutral behåller nuvarande läge.
      </p>
    </div>
    
    <div style="margin-bottom: 15px;">
      <h4 style="margin: 10px 0 5px 0; color: #666;">Felsökning</h4>
      <div class="controls">
        <button onclick="showTroubleshooting()">Visa Felstatus</button>
        <button class="danger" onclick="resetErrors()">Återställ Fel</button>
      </div>
      <p style="font-size: 12px; color: #666; margin-top: 5px;">
        Visa detaljerad felstatus och återställ pump-fel.
      </p>
    </div>
  </div>
  
  <div id="message" class="message"></div>
  <div id="troubleshooting" style="display: none; margin-top: 20px; padding: 15px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;">
    <h3 style="margin-top: 0;">Felsökningsinformation</h3>
    <pre id="troubleshooting-data" style="font-family: monospace; white-space: pre-wrap;"></pre>
  </div>
</div>

<script>
const key = localStorage.getItem('apiKey') || prompt("API Key:");
if (!key) {
  document.getElementById('status').innerText = 'Ingen API-nyckel angiven';
} else {
  localStorage.setItem('apiKey', key);
  loadStatus();
  // Auto-refresh status every 5 seconds
  setInterval(loadStatus, 5000);
}

function showMessage(msg, isError = false) {
  const msgEl = document.getElementById('message');
  msgEl.className = 'message ' + (isError ? 'error' : 'success');
  msgEl.innerText = msg;
  msgEl.style.display = 'block';
  setTimeout(() => { msgEl.style.display = 'none'; }, 5000);
}

async function loadStatus() {
  try {
    const r = await fetch('/status', {headers: {'X-API-Key': key}});
    if (!r.ok) {
      document.getElementById('status').innerText = 'Auth fel - kontrollera API-nyckel';
      return;
    }
    const d = await r.json();
    
    // Format status nicely
    const blockReasons = ['OK', 'Regn > tröskel', 'Markfukt > tröskel', 'Anti-kollision', 'E-stop'];
    const blockReason = blockReasons[d.block_reason] || `Kod ${d.block_reason}`;
    
    document.getElementById('status').innerText = 
      `Aktiv zon: ${d.zone}\\n` +
      `Pump: ${d.pump_on ? 'PÅ' : 'AV'}\\n` +
      `Steg: ${d.steg}\\n` +
      `Vald zon: ${d.selected_zone}\\n` +
      `Läge: ${d.mode_text || 'Okänd'}\\n` +
      `Block status: ${blockReason}\\n` +
      `Heartbeat: ${d.heartbeat_count}\\n` +
      `Tid: ${new Date().toLocaleTimeString('sv-SE')}`;
  } catch (err) {
    document.getElementById('status').innerText = 'Fel vid status-hämtning: ' + err.message;
  }
}

async function startManual() {
  const zone = parseInt(document.getElementById('zone').value);
  
  try {
    const r = await fetch('/command/manual', {
      method: 'POST',
      headers: {'X-API-Key': key, 'Content-Type': 'application/json'},
      body: JSON.stringify({zone})
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    const result = await r.json();
    showMessage(`Zon ${zone} startad (${result.note})`);
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function startNightProgram() {
  if (!confirm('Starta natt-program? Detta kör alla zoner enligt konfigurerade tider.')) {
    return;
  }
  
  try {
    const r = await fetch('/command/start-night-program', {
      method: 'POST',
      headers: {'X-API-Key': key}
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    const result = await r.json();
    showMessage(result.message || 'Natt-program startat');
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function startAuto() {
  try {
    const r = await fetch('/command/start-auto', {
      method: 'POST',
      headers: {'X-API-Key': key}
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    showMessage('Auto-program startat');
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function stopAll() {
  if (!confirm('Stoppa all bevattning?')) {
    return;
  }
  
  try {
    const r = await fetch('/command/stop', {
      method: 'POST',
      headers: {'X-API-Key': key}
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    showMessage('Bevattning stoppad');
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function testAllZones() {
  if (!confirm('Starta test av alla zoner? Detta tar ca 7-8 minuter (1 min per zon) och blockerar API under tiden.')) {
    return;
  }
  
  showMessage('Testar alla zoner... Detta tar några minuter.');
  
  try {
    const r = await fetch('/menu/test-bevattning', {
      method: 'POST',
      headers: {'X-API-Key': key, 'Content-Type': 'application/json'},
      body: JSON.stringify({duration_seconds: 60, all_zones_confirmed: true})
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    const result = await r.json();
    const successCount = Object.values(result.test_results).filter(v => v === 'success').length;
    showMessage(`Zontest slutfört: ${successCount}/${result.zones_tested.length} zoner testade OK`);
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function testSingleZone() {
  const zone = parseInt(document.getElementById('zone').value);
  if (!confirm(`Testa zon ${zone} i 1 minut?`)) {
    return;
  }
  
  showMessage(`Testar zon ${zone}...`);
  
  try {
    const r = await fetch('/menu/test-bevattning', {
      method: 'POST',
      headers: {'X-API-Key': key, 'Content-Type': 'application/json'},
      body: JSON.stringify({zone: zone, duration_seconds: 60})
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    const result = await r.json();
    const testResult = result.test_results[`zone_${zone}`];
    if (testResult === 'success') {
      showMessage(`Zon ${zone} testad OK`);
    } else {
      showMessage(`Zon ${zone} test misslyckades: ${testResult}`, true);
    }
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function setMode(mode) {
  const modeName = mode === 1 ? 'Auto' : 'Manuellt';
  if (!confirm(`Växla till ${modeName} läge?`)) {
    return;
  }
  
  try {
    const r = await fetch(`/menu/lagesval?mode=${mode}`, {
      method: 'POST',
      headers: {'X-API-Key': key}
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    const result = await r.json();
    showMessage(`Läge ändrat till: ${result.mode}`);
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function setSwitchMode(mode) {
  const modeNames = {0: 'Neutral', 1: 'Lokalt läge', 2: 'Fjärrläge'};
  const modeName = modeNames[mode] || 'Okänt';
  
  if (!confirm(`Växla till ${modeName}?`)) {
    return;
  }
  
  try {
    const r = await fetch(`/set-mode/${mode}`, {
      method: 'POST',
      headers: {'X-API-Key': key}
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    const result = await r.json();
    showMessage(result.mode_text);
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function showTroubleshooting() {
  try {
    const r = await fetch('/menu/felsökning', {
      headers: {'X-API-Key': key}
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    const data = await r.json();
    const formatted = JSON.stringify(data, null, 2);
    document.getElementById('troubleshooting-data').innerText = formatted;
    document.getElementById('troubleshooting').style.display = 'block';
    
    // Scroll to troubleshooting section
    document.getElementById('troubleshooting').scrollIntoView({behavior: 'smooth'});
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}

async function resetErrors() {
  if (!confirm('Återställa pump-fel och zonlogik?')) {
    return;
  }
  
  try {
    const r = await fetch('/menu/reset-error', {
      method: 'POST',
      headers: {'X-API-Key': key}
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    const result = await r.json();
    showMessage('Fel återställda: ' + result.message);
    setTimeout(loadStatus, 500);
  } catch (err) {
    showMessage('Nätverksfel: ' + err.message, true);
  }
}
</script>
</body>
</html>
"""


# Pydantic models for new endpoints
class ZoneControlCommand(BaseModel):
    """Command for controlling individual zones"""
    zone: int
    action: str  # "start" or "stop"
    duration_minutes: Optional[int] = None  # For start action


@app.get("/rain-forecast")
def get_rain_forecast(x_api_key: Optional[str] = Header(None)):
    """
    Hämta regnprognos från Open-Meteo.
    Returnerar:
    - Förväntad nederbörd nästa 24 timmar
    - Historisk nederbörd senaste 7 dagarna
    """
    require_key(x_api_key)
    
    # Använd Malmö koordinater som standard (kan göras konfigurerbar)
    latitude = float(os.getenv("LATITUDE", "55.6050"))
    longitude = float(os.getenv("LONGITUDE", "13.0038"))
    
    try:
        # Hämta prognos för nästa 24 timmar
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}"
            f"&hourly=precipitation&timezone=Europe/Stockholm"
            f"&forecast_days=2"
        )
        
        forecast_response = requests.get(forecast_url, timeout=10)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        # Hämta historisk data för senaste 7 dagarna
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        historical_url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={latitude}&longitude={longitude}"
            f"&start_date={start_date.isoformat()}"
            f"&end_date={end_date.isoformat()}"
            f"&daily=precipitation_sum&timezone=Europe/Stockholm"
        )
        
        historical_response = requests.get(historical_url, timeout=10)
        historical_response.raise_for_status()
        historical_data = historical_response.json()
        
        # Beräkna nästa 24h total nederbörd
        now = datetime.now()
        next_24h_precipitation = 0.0
        hourly_forecast = []
        
        if "hourly" in forecast_data:
            times = forecast_data["hourly"]["time"]
            precip = forecast_data["hourly"]["precipitation"]
            
            for i, time_str in enumerate(times):
                try:
                    # Handle ISO format timestamps with or without 'Z' suffix
                    if time_str.endswith('Z'):
                        time_str = time_str[:-1] + '+00:00'
                    forecast_time = datetime.fromisoformat(time_str)
                except (ValueError, AttributeError) as e:
                    logger.warning("Kunde inte tolka tidsstämpel '%s': %s", time_str, e)
                    continue
                
                if now <= forecast_time <= now + timedelta(hours=24):
                    next_24h_precipitation += precip[i] or 0.0
                    hourly_forecast.append({
                        "time": times[i],  # Use original time_str
                        "precipitation": precip[i] or 0.0
                    })
        
        # Extrahera historisk data
        daily_history = []
        if "daily" in historical_data:
            dates = historical_data["daily"]["time"]
            precip_sum = historical_data["daily"]["precipitation_sum"]
            
            for i, date_str in enumerate(dates):
                daily_history.append({
                    "date": date_str,
                    "precipitation": precip_sum[i] or 0.0
                })
        
        logger.info("Regnprognos hämtad: nästa 24h=%.1fmm, historisk data=%d dagar", 
                   next_24h_precipitation, len(daily_history))
        
        return {
            "ok": True,
            "forecast_24h": {
                "total_mm": round(next_24h_precipitation, 1),
                "hourly": hourly_forecast[:24]  # Begränsa till 24 timmar
            },
            "history_7d": {
                "daily": daily_history
            },
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "timestamp": int(time.time())
        }
        
    except requests.exceptions.RequestException as e:
        logger.error("Fel vid hämtning av väderdata: %s", e)
        raise HTTPException(
            status_code=502, 
            detail=f"Kunde inte hämta väderdata från Open-Meteo: {str(e)}"
        ) from e


@app.get("/process-view")
def get_process_view(x_api_key: Optional[str] = Header(None)):
    """
    Hämta live processtatus för grafisk visualisering.
    Returnerar:
    - Zonsstatus (aktiv/inaktiv) för alla zoner 1-7
    - Pumpstatus (på/av)
    - Felstatus (markfukt-block, regn-block, e-stop, etc.)
    - Aktuellt steg i sekvensen
    """
    require_key(x_api_key)
    logger.debug("[API_CALL] /process-view anropad - timestamp=%s", int(time.time()))
    
    with get_modbus_connection() as client:
        # Läs status-register
        status_regs = client.read_holding_registers(MW_STATUS_ZONE, 4, unit=MODBUS_UNIT)
        _ensure_modbus_ok(status_regs, "read process view status")
        
        # Läs heartbeat och fel-register
        heartbeat_regs = client.read_holding_registers(MW_HEARTBEAT, 4, unit=MODBUS_UNIT)
        _ensure_modbus_ok(heartbeat_regs, "read process view heartbeat")
        
        # Läs tröskelvärden och konfiguration
        config_regs = client.read_holding_registers(MW_TID_CENTER, 2, unit=MODBUS_UNIT)
        _ensure_modbus_ok(config_regs, "read process view config")
        
        # Läs miljödata
        env_regs = client.read_holding_registers(MW_MARKFUKT, 3, unit=MODBUS_UNIT)
        _ensure_modbus_ok(env_regs, "read process view environment")
        
        # Läs tröskelvärden för fel
        threshold_regs = client.read_holding_registers(MW_REGEN_THRESHOLD, 2, unit=MODBUS_UNIT)
        _ensure_modbus_ok(threshold_regs, "read process view thresholds")
        
        # Läs mode
        mode_reg = client.read_holding_registers(MW_MODE, 1, unit=MODBUS_UNIT)
        _ensure_modbus_ok(mode_reg, "read process view mode")
    
    current_zone = status_regs.registers[0]
    pump_on = status_regs.registers[1] == 1
    steg = status_regs.registers[2]
    selected_zone = status_regs.registers[3]
    
    eventmask = heartbeat_regs.registers[2]
    block_reason = heartbeat_regs.registers[3]
    
    # Tröskelvärden (använd default om 0)
    regen_threshold = threshold_regs.registers[0] if threshold_regs.registers[0] > 0 else 5
    moisture_threshold = threshold_regs.registers[1] if threshold_regs.registers[1] > 0 else 80
    
    # Tolka zonsstatus - aktiv zon är den som körs just nu
    zones_status = []
    for zone_num in range(1, 8):
        is_active = (current_zone == zone_num and pump_on)
        zones_status.append({
            "zone": zone_num,
            "active": is_active,
            "selected": (selected_zone == zone_num)
        })
    
    # Tolka fel och blockeringar med förklaringar
    errors = {
        "e_stop": bool(eventmask & 0x01),
        "moisture_block": bool(eventmask & 0x02) and block_reason == 2,
        "rain_block": bool(eventmask & 0x02) and block_reason == 1,
        "anti_collision": bool(eventmask & 0x08),
        "sequence_active": bool(eventmask & 0x04)
    }
    
    error_details = {
        "e_stop": {
            "active": errors["e_stop"],
            "text": "E-stop aktiv",
            "explanation": "Nödstoppet är aktiverat. Kontrollera fysisk nödstopp-knapp och systemstatus.",
            "severity": "critical"
        },
        "moisture_block": {
            "active": errors["moisture_block"],
            "text": "Markfukt-block",
            "explanation": f"Markfukten ({env_regs.registers[0]}%) är över tröskelvärdet ({moisture_threshold}%). Bevattning blockeras.",
            "severity": "warning"
        },
        "rain_block": {
            "active": errors["rain_block"],
            "text": "Regn-block",
            "explanation": f"Nederbörd senaste 24h ({env_regs.registers[1]} mm) är över tröskelvärdet ({regen_threshold} mm). Bevattning blockeras.",
            "severity": "warning"
        },
        "anti_collision": {
            "active": errors["anti_collision"],
            "text": "Anti-kollision",
            "explanation": "Pumpen är upptagen av en annan process. Vänta tills aktuell körning är klar.",
            "severity": "info"
        },
        "sequence_active": {
            "active": errors["sequence_active"],
            "text": "Sekvens aktiv",
            "explanation": f"En bevattningssekvens körs (Steg {steg}, Zon {current_zone}).",
            "severity": "info"
        }
    }
    
    # Block reason text with detailed explanations
    block_reasons = {
        0: "OK",
        1: "Regn över tröskel",
        2: "Markfukt över tröskel",
        3: "Anti-kollision/Pump upptagen",
        4: "E-stop aktiv"
    }
    
    block_explanations = {
        0: "Systemet fungerar normalt. Inga aktiva blockeringar.",
        1: f"Nederbörd senaste 24h ({env_regs.registers[1]} mm) överstiger tröskelvärdet ({regen_threshold} mm). Bevattning pausas automatiskt.",
        2: f"Markfukten ({env_regs.registers[0]}%) överstiger tröskelvärdet ({moisture_threshold}%). Bevattning pausas automatiskt.",
        3: "En annan sekvens eller process använder pumpen. Vänta tills den är klar.",
        4: "Nödstopp är aktiverat. Kontrollera fysisk E-stop-knapp och återställ innan körning."
    }
    
    mode_value = mode_reg.registers[0]
    mode_text = {
        0: "Neutral",
        1: "Lokalt läge",
        2: "Fjärrläge"
    }
    
    return {
        "ok": True,
        "zones": zones_status,
        "pump": {
            "on": pump_on,
            "status": "Aktiv" if pump_on else "Inaktiv"
        },
        "sequence": {
            "active": bool(eventmask & 0x04),
            "current_step": steg,
            "current_zone": current_zone
        },
        "errors": errors,
        "error_details": error_details,
        "block_status": {
            "code": block_reason,
            "text": block_reasons.get(block_reason, f"Okänd kod {block_reason}"),
            "explanation": block_explanations.get(block_reason, f"Okänd blockeringskod: {block_reason}"),
            "blocked": block_reason != 0
        },
        "environment": {
            "moisture_percent": env_regs.registers[0],
            "rain_24h_mm": env_regs.registers[1],
            "temperature_c": env_regs.registers[2]
        },
        "configuration": {
            "tid_center_min": config_regs.registers[0],
            "tid_horn_min": config_regs.registers[1],
            "regen_threshold_mm": regen_threshold,
            "moisture_threshold_percent": moisture_threshold
        },
        "mode": {
            "value": mode_value,
            "text": mode_text.get(mode_value, f"Okänt {mode_value}")
        },
        "timestamp": int(time.time())
    }


@app.post("/zone-control")
def zone_control(cmd: ZoneControlCommand, x_api_key: Optional[str] = Header(None)):
    """
    Styr individuella zoner via webb-gränssnittet.
    Åtgärder:
    - start: Starta vald zon (kräver duration_minutes om inte default används)
    - stop: Stoppa all bevattning
    """
    require_key(x_api_key)
    
    zone = validate_zone(cmd.zone)
    logger.info("[USER_ACTION] zone-control anropad - zon=%s action=%s timestamp=%s", 
                zone, cmd.action, int(time.time()))
    
    if cmd.action == "start":
        logger.info("[ZONE_EVENT] Zon %s STARTAS via process view", zone)
        
        # Sätt vald zon och starta manuell körning
        with get_modbus_connection() as client:
            rr = client.write_register(MW_SET_SELECTED, zone, unit=MODBUS_UNIT)
            _ensure_modbus_ok(rr, f"set zone {zone} via zone-control")
            
            # Pulsera manuell start
            rr = client.write_register(MW_MANUAL_START, 1, unit=MODBUS_UNIT)
            _ensure_modbus_ok(rr, f"start zone {zone} via zone-control")
        
        logger.info("[ZONE_EVENT] Zon %s STARTAD - använder auto-tider", zone)
        return {
            "ok": True,
            "action": "start",
            "zone": zone,
            "message": f"Zon {zone} startad (använder auto-tider)"
        }
    
    elif cmd.action == "stop":
        logger.info("[PUMP_EVENT] STOPP-kommando för zon %s via process view", zone)
        
        with get_modbus_connection() as client:
            rr = client.write_register(MW_REMOTE_CMD, 0, unit=MODBUS_UNIT)
            _ensure_modbus_ok(rr, "stop via zone-control")
            
            rr = client.write_register(MW_MODE_OVERRIDE, 0, unit=MODBUS_UNIT)
            _ensure_modbus_ok(rr, "reset mode override via zone-control")
        
        logger.info("[PUMP_EVENT] Bevattning STOPPAD via process view")
        return {
            "ok": True,
            "action": "stop",
            "zone": zone,
            "message": "Bevattning stoppad"
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Ogiltig åtgärd '{cmd.action}'. Tillåtna: 'start', 'stop'"
        )


# ============================================================================
# User Management Endpoints (Superadmin Only)
# ============================================================================

class CreateUserRequest(BaseModel):
    """Request model for creating a user."""
    username: str
    password: str
    is_admin: bool = False


class DeleteUserRequest(BaseModel):
    """Request model for deleting a user."""
    username: str


@app.post("/users/create")
def create_user(
    request: CreateUserRequest,
    _superadmin: str = Depends(require_superadmin)
):
    """
    Create a new user account (superadmin only).
    
    Requires HTTP Basic Authentication with superadmin credentials.
    Password must be at least 8 characters long.
    """
    if user_manager is None:
        raise HTTPException(
            status_code=503,
            detail="User management not available - missing dependencies"
        )
    
    logger.info("[SUPERADMIN] Creating user: %s (admin=%s)", request.username, request.is_admin)
    
    try:
        success = user_manager.create_user(
            username=request.username,
            password=request.password,
            is_admin=request.is_admin
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"User '{request.username}' already exists"
            )
        
        logger.info("[SUPERADMIN] User created successfully: %s", request.username)
        return {
            "ok": True,
            "message": f"User '{request.username}' created successfully",
            "username": request.username,
            "is_admin": request.is_admin
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[SUPERADMIN] Failed to create user: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create user") from e


@app.post("/users/delete")
def delete_user(
    request: DeleteUserRequest,
    _superadmin: str = Depends(require_superadmin)
):
    """
    Delete a user account (superadmin only).
    
    Requires HTTP Basic Authentication with superadmin credentials.
    """
    if user_manager is None:
        raise HTTPException(
            status_code=503,
            detail="User management not available - missing dependencies"
        )
    
    logger.info("[SUPERADMIN] Deleting user: %s", request.username)
    
    try:
        success = user_manager.delete_user(request.username)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"User '{request.username}' not found"
            )
        
        logger.info("[SUPERADMIN] User deleted successfully: %s", request.username)
        return {
            "ok": True,
            "message": f"User '{request.username}' deleted successfully",
            "username": request.username
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[SUPERADMIN] Failed to delete user: %s", e)
        raise HTTPException(status_code=500, detail="Failed to delete user") from e


@app.get("/users/list")
def list_users(_superadmin: str = Depends(require_superadmin)):
    """
    List all user accounts (superadmin only).
    
    Requires HTTP Basic Authentication with superadmin credentials.
    Returns a list of users without password hashes.
    """
    if user_manager is None:
        raise HTTPException(
            status_code=503,
            detail="User management not available - missing dependencies"
        )
    
    logger.info("[SUPERADMIN] Listing all users")
    
    try:
        users = user_manager.list_users()
        return {
            "ok": True,
            "users": users,
            "count": len(users)
        }
    
    except Exception as e:
        logger.error("[SUPERADMIN] Failed to list users: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list users") from e
