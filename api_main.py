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


def _pulse_remote_command(value: int, pulse_seconds: float = 1.0):
    """Helper function to pulse Remote_Command register"""
    with get_modbus_connection() as client:
        rr = client.write_register(MW_REMOTE_CMD, value, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
        time.sleep(pulse_seconds)
        rr = client.write_register(MW_REMOTE_CMD, 0, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")


@app.post("/command/start-auto")
def start_auto(x_api_key: Optional[str] = Header(None), pulse_seconds: float = 1.0):
    require_key(x_api_key)
    _pulse_remote_command(50, pulse_seconds)
    return {"ok": True}


@app.post("/command/start-night-program")
def start_night_program(x_api_key: Optional[str] = Header(None), pulse_seconds: float = 1.0):
    """
    Starta natt-program (kör alla zoner som auto-mode).
    Detta tvingar fram en "natt körning" genom att aktivera auto-mode.
    """
    require_key(x_api_key)
    _pulse_remote_command(50, pulse_seconds)
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
    # Write selected zone and pulse manual start
    with get_modbus_connection() as client:
        rr = client.write_register(MW_SET_SELECTED, zone, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
        # Pulse manual start
        rr = client.write_register(MW_MANUAL_START, 1, unit=MODBUS_UNIT)
        if rr is None or (hasattr(rr, "isError") and rr.isError()):
            raise HTTPException(status_code=502, detail="Modbus write error")
    return {"ok": True, "zone": zone, "note": "Manual mode runs only the selected zone using auto times"}


@app.post("/command/set-zone")
def set_zone(cmd: SetZone, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    zone = validate_zone(cmd.zone)
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
    # Reuse connection for multiple writes - connection already optimized
    with get_modbus_connection() as client:
        # Optimize: Use bulk write for consecutive registers MW20-21 when both provided
        if cfg.tid_center is not None and cfg.tid_horn is not None:
            values = [clamp_tid_center(cfg.tid_center), clamp_tid_horn(cfg.tid_horn)]
            rr = client.write_registers(MW_TID_CENTER, values, unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        else:
            if cfg.tid_center is not None:
                rr = client.write_register(MW_TID_CENTER, clamp_tid_center(cfg.tid_center), unit=MODBUS_UNIT)
                if rr is None or (hasattr(rr, "isError") and rr.isError()):
                    raise HTTPException(status_code=502, detail="Modbus write error")
            if cfg.tid_horn is not None:
                rr = client.write_register(MW_TID_HORN, clamp_tid_horn(cfg.tid_horn), unit=MODBUS_UNIT)
                if rr is None or (hasattr(rr, "isError") and rr.isError()):
                    raise HTTPException(status_code=502, detail="Modbus write error")
        
        # Optimize: Use bulk write for consecutive registers MW30-32 when all three provided
        if cfg.markfukt is not None and cfg.regen24 is not None and cfg.temp_c is not None:
            values = [clamp_markfukt(cfg.markfukt), 
                     clamp_regen(cfg.regen24), 
                     clamp_temp(cfg.temp_c)]
            rr = client.write_registers(MW_MARKFUKT, values, unit=MODBUS_UNIT)
            if rr is None or (hasattr(rr, "isError") and rr.isError()):
                raise HTTPException(status_code=502, detail="Modbus write error")
        else:
            if cfg.markfukt is not None:
                rr = client.write_register(MW_MARKFUKT, clamp_markfukt(cfg.markfukt), unit=MODBUS_UNIT)
                if rr is None or (hasattr(rr, "isError") and rr.isError()):
                    raise HTTPException(status_code=502, detail="Modbus write error")
            if cfg.regen24 is not None:
                rr = client.write_register(MW_REGEN24, clamp_regen(cfg.regen24), unit=MODBUS_UNIT)
                if rr is None or (hasattr(rr, "isError") and rr.isError()):
                    raise HTTPException(status_code=502, detail="Modbus write error")
            if cfg.temp_c is not None:
                rr = client.write_register(MW_TEMP, clamp_temp(cfg.temp_c), unit=MODBUS_UNIT)
                if rr is None or (hasattr(rr, "isError") and rr.isError()):
                    raise HTTPException(status_code=502, detail="Modbus write error")
        
        # manual_time is deprecated - kept for backward compatibility but does nothing
        if cfg.manual_time is not None:
            # No-op for backward compatibility
            pass
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
      
      <label>Körtid:</label>
      <input type="number" id="minutes" value="5" min="1" max="240" style="width: 80px;">
      <span>minuter</span>
      
      <button onclick="startManual()">Starta Zon</button>
    </div>
    <p style="font-size: 12px; color: #666; margin-top: 10px;">
      Standard körtid är 5 minuter. Justera innan start om annat önskas.
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
  
  <div id="message" class="message"></div>
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
      `Block status: ${blockReason}\\n` +
      `Heartbeat: ${d.heartbeat_count}\\n` +
      `Tid: ${new Date().toLocaleTimeString('sv-SE')}`;
  } catch (err) {
    document.getElementById('status').innerText = 'Fel vid status-hämtning: ' + err.message;
  }
}

async function startManual() {
  const zone = parseInt(document.getElementById('zone').value);
  const minutes = parseInt(document.getElementById('minutes').value);
  
  if (minutes < 1 || minutes > 240) {
    showMessage('Körtid måste vara 1-240 minuter', true);
    return;
  }
  
  try {
    const r = await fetch('/command/manual', {
      method: 'POST',
      headers: {'X-API-Key': key, 'Content-Type': 'application/json'},
      body: JSON.stringify({zone, minutes})
    });
    
    if (!r.ok) {
      const err = await r.json();
      showMessage('Fel: ' + (err.detail || 'Okänt fel'), true);
      return;
    }
    
    showMessage(`Zon ${zone} startad för ${minutes} minuter`);
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
</script>
</body>
</html>
"""
