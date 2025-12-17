import os
import time
from typing import Optional
from contextlib import contextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

try:
    from pymodbus.client import ModbusTcpClient
except Exception:
    try:
        from pymodbus.client.sync import ModbusTcpClient
    except Exception:
        ModbusTcpClient = None

load_dotenv()

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
MW_STATUS_ZONE = 50
MW_STATUS_PUMP = 51
MW_STATUS_STEG = 52
MW_SELECTED_ZONE = 53
MW_MODE_OVERRIDE = 60
MW_MANUAL_START = 61
MW_SET_SELECTED = 63
MW_MANUAL_TIME = 64
MW_HEARTBEAT = 70
MW_HEARTBEAT_CNT = 71
MW_EVENTMASK = 72
MW_BLOCK_REASON = 73

app = FastAPI(title="Bevattning API", version="0.2")


def require_key(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def validate_zone(value: int) -> int:
    if value < 1 or value > 7:
        raise HTTPException(status_code=400, detail="zone must be 1..7")
    return value


def validate_minutes(value: int) -> int:
    if value < 1 or value > 240:
        raise HTTPException(status_code=400, detail="minutes must be 1..240")
    return value


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
            raise HTTPException(status_code=502, detail="Modbus connect failed")
        yield client
    finally:
        try:
            client.close()
        except Exception:
            pass


def read_regs(address, count=1):
    with get_modbus_connection() as client:
        rr = client.read_holding_registers(address, count, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus read error")
        return rr.registers


def write_reg(address, value):
    with get_modbus_connection() as client:
        rr = client.write_register(address, int(value), unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
        return True


def write_regs_bulk(start_address, values):
    """Write multiple registers at once for better performance."""
    with get_modbus_connection() as client:
        rr = client.write_registers(start_address, [int(v) for v in values], unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
        return True


class ManualCommand(BaseModel):
    zone: int
    minutes: Optional[int] = None  # om None används befintligt MW64
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
    manual_time: Optional[int] = None  # MW64
    mode_override: Optional[int] = None  # 1=Auto, 0=Manual


@app.get("/status")
def status(x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    # Read registers in two groups to avoid reading undefined intermediate registers.
    # According to the PLC register map, MW54-59, MW62, MW65-69 are not defined.
    # Reading only defined registers prevents potential issues with non-existent or 
    # side-effect registers while still being more efficient than the original implementation.
    # Group 1: MW50-53 (zone, pump, steg, selected_zone)
    # Group 2: MW70-73 (heartbeat data)
    with get_modbus_connection() as client:
        rr1 = client.read_holding_registers(MW_STATUS_ZONE, 4, unit=MODBUS_UNIT)
        if rr1 is None or (hasattr(rr1, "isError") and rr1.isError()):
            raise HTTPException(status_code=502, detail="Modbus read error")
        rr2 = client.read_holding_registers(MW_HEARTBEAT, 4, unit=MODBUS_UNIT)
        if rr2 is None or (hasattr(rr2, "isError") and rr2.isError()):
            raise HTTPException(status_code=502, detail="Modbus read error")
    
    return {
        "zone": rr1.registers[0],
        "pump_on": rr1.registers[1] == 1,
        "steg": rr1.registers[2],
        "selected_zone": rr1.registers[3],
        "heartbeat_bit": rr2.registers[0],
        "heartbeat_count": rr2.registers[1],
        "eventmask": rr2.registers[2],
        "block_reason": rr2.registers[3],
        "timestamp": int(time.time())
    }


@app.post("/command/start-auto")
def start_auto(x_api_key: Optional[str] = Header(None), pulse_seconds: float = 1.0):
    require_key(x_api_key)
    # Reuse connection for pulse operation
    with get_modbus_connection() as client:
        rr = client.write_register(MW_REMOTE_CMD, 50, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
        time.sleep(pulse_seconds)
        rr = client.write_register(MW_REMOTE_CMD, 0, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
    return {"ok": True}


@app.post("/command/manual")
def start_manual(cmd: ManualCommand, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    zone = validate_zone(cmd.zone)
    minutes = cmd.minutes
    # Reuse connection for multiple writes
    with get_modbus_connection() as client:
        if cmd.minutes is not None:
            minutes = validate_minutes(cmd.minutes)
            rr = client.write_register(MW_MANUAL_TIME, minutes, unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        rr = client.write_register(MW_SET_SELECTED, zone, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
        # Pulse manual start
        rr = client.write_register(MW_MANUAL_START, 1, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
    return {"ok": True, "zone": zone, "minutes": minutes}


@app.post("/command/set-zone")
def set_zone(cmd: SetZone, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    zone = validate_zone(cmd.zone)
    write_reg(MW_SET_SELECTED, zone)
    return {"ok": True, "zone": zone}


@app.post("/command/set-manual-time")
def set_manual_time(cmd: SetManualTime, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    minutes = validate_minutes(cmd.minutes)
    write_reg(MW_MANUAL_TIME, minutes)
    return {"ok": True, "minutes": minutes}


@app.post("/command/stop")
def stop(x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    # Reuse connection for multiple writes
    with get_modbus_connection() as client:
        rr = client.write_register(MW_REMOTE_CMD, 0, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
        rr = client.write_register(MW_MODE_OVERRIDE, 0, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
    return {"ok": True}


@app.post("/config")
def config(cfg: ConfigUpdate, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    # Reuse connection for multiple writes
    with get_modbus_connection() as client:
        if cfg.tid_center is not None:
            rr = client.write_register(MW_TID_CENTER, max(0, min(240, cfg.tid_center)), unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        if cfg.tid_horn is not None:
            rr = client.write_register(MW_TID_HORN, max(0, min(240, cfg.tid_horn)), unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        if cfg.markfukt is not None:
            rr = client.write_register(MW_MARKFUKT, max(0, min(100, cfg.markfukt)), unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        if cfg.regen24 is not None:
            rr = client.write_register(MW_REGEN24, max(0, min(500, cfg.regen24)), unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        if cfg.temp_c is not None:
            rr = client.write_register(MW_TEMP, max(-30, min(50, cfg.temp_c)), unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        if cfg.manual_time is not None:
            rr = client.write_register(MW_MANUAL_TIME, max(1, min(240, cfg.manual_time)), unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        if cfg.mode_override is not None:
            rr = client.write_register(MW_MODE_OVERRIDE, 1 if cfg.mode_override == 1 else 0, unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<!doctype html>
<html>
<head><title>Bevattning</title></head>
<body>
<h2>Bevattning status</h2>
<div id="out">Laddar...</div>
<script>
const key = localStorage.getItem('apiKey') || prompt("API Key:");
localStorage.setItem('apiKey', key);
async function load() {
  const r = await fetch('/status', {headers: {'X-API-Key': key}});
  if (!r.ok) { document.getElementById('out').innerText = 'Auth fail'; return; }
  const d = await r.json();
  document.getElementById('out').innerText = JSON.stringify(d, null, 2);
}
load();
</script>
</body>
</html>
"""
