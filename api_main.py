import os
import time
from typing import Optional

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


def mb_client():
    if ModbusTcpClient is None:
        raise HTTPException(status_code=500, detail="pymodbus not installed")
    return ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT, timeout=3)


def read_regs(address, count=1):
    client = mb_client()
    if not client.connect():
        raise HTTPException(status_code=502, detail="Modbus connect failed")
    rr = client.read_holding_registers(address, count, unit=MODBUS_UNIT)
    client.close()
    if rr is None or (hasattr(rr, "isError") and rr.isError()):
        raise HTTPException(status_code=502, detail="Modbus read error")
    return rr.registers


def write_reg(address, value):
    client = mb_client()
    if not client.connect():
        raise HTTPException(status_code=502, detail="Modbus connect failed")
    rr = client.write_register(address, int(value), unit=MODBUS_UNIT)
    client.close()
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
    regs = read_regs(MW_STATUS_ZONE, 9)  # 50-58 (we need 50-53, 70-73 nearby)
    zone = regs[0]
    pump = regs[1]
    steg = regs[2]
    selected = regs[3]
    hb = read_regs(MW_HEARTBEAT, 4)
    return {
        "zone": zone,
        "pump_on": pump == 1,
        "steg": steg,
        "selected_zone": selected,
        "heartbeat_bit": hb[0],
        "heartbeat_count": hb[1],
        "eventmask": hb[2],
        "block_reason": hb[3],
        "timestamp": int(time.time())
    }


@app.post("/command/start-auto")
def start_auto(x_api_key: Optional[str] = Header(None), pulse_seconds: float = 1.0):
    require_key(x_api_key)
    # Puls MW10 = 50 -> 0
    write_reg(MW_REMOTE_CMD, 50)
    time.sleep(pulse_seconds)
    write_reg(MW_REMOTE_CMD, 0)
    return {"ok": True}


@app.post("/command/manual")
def start_manual(cmd: ManualCommand, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    if cmd.zone < 1 or cmd.zone > 7:
        raise HTTPException(status_code=400, detail="zone must be 1..7")
    if cmd.minutes is not None:
        write_reg(MW_MANUAL_TIME, max(1, min(240, cmd.minutes)))
    write_reg(MW_SET_SELECTED, cmd.zone)
    # Puls manual start
    write_reg(MW_MANUAL_START, 1)
    return {"ok": True, "zone": cmd.zone, "minutes": cmd.minutes}


@app.post("/command/set-zone")
def set_zone(cmd: SetZone, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    if cmd.zone < 1 or cmd.zone > 7:
        raise HTTPException(status_code=400, detail="zone must be 1..7")
    write_reg(MW_SET_SELECTED, cmd.zone)
    return {"ok": True, "zone": cmd.zone}


@app.post("/command/set-manual-time")
def set_manual_time(cmd: SetManualTime, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    if cmd.minutes < 1 or cmd.minutes > 240:
        raise HTTPException(status_code=400, detail="minutes must be 1..240")
    write_reg(MW_MANUAL_TIME, cmd.minutes)
    return {"ok": True, "minutes": cmd.minutes}


@app.post("/command/stop")
def stop(x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    # Skriv ModeOverride=0 (Manual) och trigga Stop via Stop_Puls motsvarighet? Här: sätt Remote_Command=0, Mode=Manual, blockar auto.
    write_reg(MW_REMOTE_CMD, 0)
    write_reg(MW_MODE_OVERRIDE, 0)
    return {"ok": True}


@app.post("/config")
def config(cfg: ConfigUpdate, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    if cfg.tid_center is not None:
        write_reg(MW_TID_CENTER, max(0, min(240, cfg.tid_center)))
    if cfg.tid_horn is not None:
        write_reg(MW_TID_HORN, max(0, min(240, cfg.tid_horn)))
    if cfg.markfukt is not None:
        write_reg(MW_MARKFUKT, max(0, min(100, cfg.markfukt)))
    if cfg.regen24 is not None:
        write_reg(MW_REGEN24, max(0, min(500, cfg.regen24)))
    if cfg.temp_c is not None:
        write_reg(MW_TEMP, max(-30, min(50, cfg.temp_c)))
    if cfg.manual_time is not None:
        write_reg(MW_MANUAL_TIME, max(1, min(240, cfg.manual_time)))
    if cfg.mode_override is not None:
        write_reg(MW_MODE_OVERRIDE, 1 if cfg.mode_override == 1 else 0)
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
