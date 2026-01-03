#!/usr/bin/env python3
"""
Digital Input Monitor - Web UI
Visar realtids-status för alla digitala ingångar (DI1-DI12) via webb
"""
from flask import Flask, jsonify, render_template_string, session, redirect, url_for, request
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import secrets
import requests
from dotenv import load_dotenv

load_dotenv("api_.env")

# Importera Modbus-klient
try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    from pymodbus.client.sync import ModbusTcpClient

# Importera DI-konfiguration
from di_config import get_di_info, get_status_text, is_alarm

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
CORS(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modbus-konfiguration
MODBUS_HOST = os.getenv('MODBUS_HOST', '127.0.0.1')
MODBUS_PORT = int(os.getenv('MODBUS_PORT', '502'))
MODBUS_UNIT = int(os.getenv('MODBUS_UNIT', '1'))
API_BASE = os.getenv('API_URL', 'http://localhost:8000')


# Flask-Login User class
class User(UserMixin):
    def __init__(self, username, is_admin=False):
        self.id = username
        self.username = username
        self.is_admin = is_admin


@login_manager.user_loader
def load_user(user_id):
    """Load user from session"""
    if 'username' in session:
        return User(session['username'], session.get('is_admin', False))
    return None

# DI-beskrivningar
DI_DESCRIPTIONS = {
    0: "Stoppknapp S202",
    1: "Startknapp S201",
    2: "Nödstopp S205 (NC)",
    3: "Resetknapp S203",
    4: "Auto-läge S204",
    5: "Manuell-läge S204",
    6: "Flödesvakt",
    7: "Mjukstartare Fault (NC)",
    8: "Tryckvakt",
    9: "Motorskydd Q1 (NC)",
    10: "24VDC Säkring (NC)",
    11: "24VAC Säkring (NC)"
}


def read_digital_inputs():
    """Läs alla DI från Modbus"""
    try:
        client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT, timeout=2)
        if not client.connect():
            return None, "Kunde inte ansluta till Modbus"
        
        # Läs discrete inputs (0-11 = DI1-DI12)
        # Pymodbus 3.x syntax: read_discrete_inputs(address, count=, device_id=)
        result = client.read_discrete_inputs(0, count=12, device_id=MODBUS_UNIT)
        client.close()
        
        if result is None or (hasattr(result, 'isError') and result.isError()):
            return None, "Modbus-läsfel"
        
        return result.bits[:12], None
        
    except Exception as e:
        return None, str(e)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login-sida"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # Verifiera mot API
        try:
            r = requests.get(
                f'{API_BASE}/users/list',
                auth=(username, password),
                timeout=2
            )
            
            if r.status_code == 200:
                session['username'] = username
                session['password'] = password
                session['is_admin'] = False
                
                user = User(username, session.get('is_admin', False))
                login_user(user)
                
                return jsonify({'ok': True})
            else:
                return jsonify({'ok': False, 'error': 'Felaktigt användarnamn eller lösenord'}), 401
        except Exception as e:
            return jsonify({'ok': False, 'error': f'Anslutningsfel: {str(e)}'}), 500
    
    return render_template_string(LOGIN_TEMPLATE)


@app.route('/logout')
@login_required
def logout():
    """Logga ut"""
    logout_user()
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Visa DI-monitor UI"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/assets/logo')
def serve_logo():
    """Servera IK Kamp logga"""
    from flask import send_file, abort
    import pathlib
    logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'ik_kamp_logo.jpg')
    
    # Verifiera att filen finns
    if not pathlib.Path(logo_path).exists():
        abort(404, description="Logo not found")
    
    return send_file(logo_path, mimetype='image/jpeg')


@app.route('/api/digital-inputs')
@login_required
def get_digital_inputs():
    """API endpoint för DI-status"""
    bits, error = read_digital_inputs()
    
    if error:
        return jsonify({
            "ok": False,
            "error": error
        }), 503
    
    # Bygg status-lista
    inputs = []
    for i in range(12):
        di_num = i + 1
        gpio_state = bits[i]
        config = get_di_info(i)
        
        inputs.append({
            "di": f"DI{di_num}",
            "name": DI_DESCRIPTIONS.get(i, f"DI{di_num}"),
            "raw_value": gpio_state,
            "status": get_status_text(i, gpio_state),
            "is_alarm": is_alarm(i, gpio_state),
            "is_active": not gpio_state if config.get('type') == 'NO' else gpio_state,
            "type": config.get('type', 'NO'),
            "critical": config.get('critical', False),
            "note": config.get('note')
        })
    
    return jsonify({
        "ok": True,
        "inputs": inputs,
        "timestamp": int(os.times().elapsed * 1000)
    })


LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logga in - DI Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #5568d3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
        .error.visible {
            display: block;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔌 DI Monitor</h1>
        <div id="error" class="error"></div>
        <form id="loginForm" onsubmit="handleLogin(event)">
            <div class="form-group">
                <label for="username">Användarnamn</label>
                <input type="text" id="username" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Lösenord</label>
                <input type="password" id="password" required>
            </div>
            <button type="submit" id="loginBtn">Logga in</button>
        </form>
    </div>
    
    <script>
        async function handleLogin(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const btn = document.getElementById('loginBtn');
            const error = document.getElementById('error');
            
            btn.disabled = true;
            btn.textContent = 'Loggar in...';
            error.classList.remove('visible');
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                
                if (data.ok) {
                    window.location.href = '/';
                } else {
                    error.textContent = data.error || 'Inloggning misslyckades';
                    error.classList.add('visible');
                }
            } catch (err) {
                error.textContent = 'Anslutningsfel: ' + err.message;
                error.classList.add('visible');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Logga in';
            }
        }
    </script>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DI Monitor - Digitala Ingångar</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Mobil-anpassningar */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            padding: 30px;
        }
        
        h1 {
            text-align: center;
            color: #333;
            margin: 0 0 10px 0;
            font-size: 32px;
        }
        
        .subtitle {
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }
        
        .update-info {
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-bottom: 20px;
        }
        
        .di-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        /* Mobil: en kolumn, mindre minsta bredd */
        @media (max-width: 768px) {
            h1 {
                font-size: 24px;
            }
            .di-grid {
                grid-template-columns: 1fr;
                gap: 12px;
            }
        }
        
        .di-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #28a745;
            transition: all 0.3s ease;
            min-height: 80px;
        }
        
        /* Mobil: större touch-area */
        @media (max-width: 768px) {
            .di-card {
                padding: 18px;
                min-height: 90px;
            }
        }
        
        .di-card.active {
            border-left-color: #2196F3;
            background: #e3f2fd;
        }
        
        .di-card.alarm {
            border-left-color: #ff9800;
            background: #fff3e0;
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        .di-card.critical.alarm {
            border-left-color: #d32f2f;
            background: #ffebee;
            animation: pulse-critical 1s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.85; }
        }
        
        @keyframes pulse-critical {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.9; transform: scale(1.02); }
        }
        
        .di-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .di-number {
            font-weight: bold;
            font-size: 18px;
            color: #333;
        }
        
        .di-status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        
        /* Mobil: större text för bättre läsbarhet */
        @media (max-width: 768px) {
            .di-number {
                font-size: 20px;
            }
            .di-status {
                padding: 6px 14px;
                font-size: 13px;
            }
        }
        
        .di-status.ok {
            background: #d4edda;
            color: #155724;
        }
        
        .di-status.active {
            background: #e3f2fd;
            color: #1565c0;
        }
        
        .di-status.alarm {
            background: #fff3e0;
            color: #e65100;
        }
        
        .di-status.critical {
            background: #d32f2f;
            color: white;
        }
        
        .di-name {
            font-size: 14px;
            color: #555;
            margin-bottom: 5px;
        }
        
        .di-type {
            font-size: 11px;
            color: #888;
            font-family: monospace;
        }
        
        .di-note {
            font-size: 11px;
            color: #666;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #ddd;
            font-style: italic;
        }
        
        .error-banner {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
            border: 1px solid #f5c6cb;
        }
        
        .legend {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        /* Mobil: mindre gap, vertikal layout */
        @media (max-width: 768px) {
            .legend {
                gap: 12px;
                font-size: 12px;
            }
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #666;
        }
        
        .legend-box {
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }
        
        .value-display {
            font-family: monospace;
            font-size: 12px;
            color: #888;
            margin-top: 3px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="/assets/logo" alt="IK Kamp" style="width: 60px; height: 60px; margin-bottom: 10px;">
        </div>
        <h1>🔌 Digital Input Monitor</h1>
        <div class="subtitle">Realtidsövervakning av knappar och sensorer</div>
        <div class="update-info" id="update-info">Uppdaterar...</div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-box" style="background: #d4edda;"></div>
                <span>OK / Inaktiv</span>
            </div>
            <div class="legend-item">
                <div class="legend-box" style="background: #e3f2fd;"></div>
                <span>✓ Tryckt / Aktiv</span>
            </div>
            <div class="legend-item">
                <div class="legend-box" style="background: #fff3e0;"></div>
                <span>⚠️ Larm (sensor)</span>
            </div>
            <div class="legend-item">
                <div class="legend-box" style="background: #d32f2f;"></div>
                <span>🚨 Kritiskt Larm</span>
            </div>
        </div>
        
        <div id="error-container"></div>
        <div id="di-container" class="di-grid">
            <p style="text-align: center; color: #999;">Laddar...</p>
        </div>
    </div>
    
    <script>
        let lastData = null;
        
        async function updateDI() {
            try {
                const response = await fetch('/api/digital-inputs');
                const data = await response.json();
                
                if (!data.ok) {
                    showError(data.error);
                    return;
                }
                
                hideError();
                renderDI(data.inputs);
                
                // Uppdatera timestamp
                const now = new Date().toLocaleTimeString('sv-SE');
                document.getElementById('update-info').innerText = `Senast uppdaterad: ${now}`;
                
                lastData = data;
            } catch (error) {
                showError('Nätverksfel: ' + error.message);
            }
        }
        
        function showError(message) {
            const container = document.getElementById('error-container');
            container.innerHTML = `<div class="error-banner">⚠️ ${message}</div>`;
        }
        
        function hideError() {
            document.getElementById('error-container').innerHTML = '';
        }
        
        function renderDI(inputs) {
            const container = document.getElementById('di-container');
            let html = '';
            
            for (const input of inputs) {
                let cardClass = 'di-card';
                let statusClass = 'di-status ok';
                
                if (input.is_alarm) {
                    cardClass += ' alarm';
                    statusClass = input.critical ? 'di-status critical' : 'di-status alarm';
                } else if (input.is_active && input.type === 'NO') {
                    cardClass += ' active';
                    statusClass = 'di-status active';
                }
                
                if (input.critical) {
                    cardClass += ' critical';
                }
                
                html += `
                    <div class="${cardClass}">
                        <div class="di-header">
                            <span class="di-number">${input.di}</span>
                            <span class="${statusClass}">${input.status}</span>
                        </div>
                        <div class="di-name">${input.name}</div>
                        <div class="di-type">Type: ${input.type} | GPIO: ${input.raw_value ? 'HIGH' : 'LOW'}</div>
                        <div class="value-display">Raw: ${input.raw_value} (${input.raw_value ? '1' : '0'})</div>
                        ${input.note ? `<div class="di-note">${input.note}</div>` : ''}
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        // Initial load
        updateDI();
        
        // Auto-refresh every 500ms for responsive button monitoring
        setInterval(updateDI, 500);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.getenv('DI_MONITOR_PORT', '8081'))
    print(f"Starting DI Monitor on port {port}")
    print(f"Open: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)

