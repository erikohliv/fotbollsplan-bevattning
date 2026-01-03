#!/usr/bin/env python3
"""
Dashboard Hub - Central kontrollpanel för bevattningssystemet
Visar översikt och länkar till alla webbgränssnitt
"""
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv("api_.env")

app = Flask(__name__)
CORS(app)

# Konfiguration
API_KEY = os.getenv('API_KEY', 'kamp')
BASE_IP = os.getenv('DASHBOARD_IP', '10.219.1.116')

# Webb-gränssnitt
SERVICES = {
    'api': {'name': 'Bevattning API', 'icon': '💧', 'port': 8000, 'url': f'http://{BASE_IP}:8000', 'desc': 'Huvudstyrning'},
    'di': {'name': 'DI Monitor', 'icon': '🔌', 'port': 8081, 'url': f'http://{BASE_IP}:8081', 'desc': 'Digitala Ingångar'},
    'users': {'name': 'Användarhantering', 'icon': '👥', 'port': 8082, 'url': f'http://{BASE_IP}:8082', 'desc': 'Användaradministration'},
    'process': {'name': 'Process View', 'icon': '📊', 'port': 8050, 'url': f'http://{BASE_IP}:8050', 'desc': 'Grafisk Övervakning'},
    'todo': {'name': 'TODO Checklist', 'icon': '📋', 'port': 8080, 'url': f'http://{BASE_IP}:8080', 'desc': 'Projekthantering'}
}


def get_system_status():
    """Hämta snabb systemöversikt"""
    try:
        # Försök hämta från API
        r = requests.get(f'http://localhost:8000/status', 
                        headers={'X-API-Key': API_KEY}, 
                        timeout=1)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    
    return {
        'zone': 0,
        'pump_on': False,
        'mode_text': 'Okänd',
        'relay_state': 0
    }


def get_di_status():
    """Hämta DI-status för varningar"""
    try:
        r = requests.get(f'http://localhost:8081/api/digital-inputs', timeout=1)
        if r.status_code == 200:
            data = r.json()
            if data.get('ok'):
                return data.get('inputs', [])
    except:
        pass
    return []


def check_service_health(port):
    """Kontrollera om en tjänst svarar"""
    try:
        r = requests.get(f'http://localhost:{port}/', timeout=1)
        return r.status_code < 500
    except:
        return False


@app.route('/')
def index():
    """Visa Dashboard Hub"""
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


@app.route('/api/overview')
def get_overview():
    """API endpoint för dashboard-översikt"""
    system = get_system_status()
    di_inputs = get_di_status()
    
    # Kontrollera tjänsternas hälsa
    services_health = {}
    for key, service in SERVICES.items():
        services_health[key] = check_service_health(service['port'])
    
    # Hitta aktiva larm från DI
    alarms = []
    critical_alarms = []
    for di in di_inputs:
        if di.get('is_alarm'):
            alarm_info = {
                'di': di['di'],
                'name': di['name'],
                'critical': di.get('critical', False)
            }
            if di.get('critical'):
                critical_alarms.append(alarm_info)
            else:
                alarms.append(alarm_info)
    
    return jsonify({
        'ok': True,
        'system': {
            'zone': system.get('zone', 0),
            'pump_on': system.get('pump_on', False),
            'mode': system.get('mode_text', 'Okänd'),
            'relay_state': system.get('relay_state', 0)
        },
        'alarms': {
            'critical': critical_alarms,
            'normal': alarms,
            'total': len(critical_alarms) + len(alarms)
        },
        'services': services_health,
        'timestamp': datetime.now().isoformat()
    })


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Bevattning Kontrollcentral</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e22ce 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.4);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }
        
        .logo {
            width: 80px;
            height: 80px;
            margin: 0 auto 15px auto;
            display: block;
            border-radius: 50%;
            background: white;
            padding: 5px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .header h1 {
            font-size: 42px;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header .subtitle {
            font-size: 16px;
            opacity: 0.9;
            color: #cbd5e0;
        }
        
        .time-display {
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 14px;
            opacity: 0.8;
        }
        
        /* Mobil: mindre header, dölj eller flytta tid */
        @media (max-width: 768px) {
            .header {
                padding: 25px 20px;
            }
            .logo {
                width: 60px;
                height: 60px;
            }
            .header h1 {
                font-size: 24px;
            }
            .header .subtitle {
                font-size: 13px;
            }
            .time-display {
                position: static;
                text-align: center;
                margin-top: 10px;
                font-size: 12px;
            }
        }
        
        .content {
            padding: 40px;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        /* Mobil: 2 kolumner, mindre gap */
        @media (max-width: 768px) {
            .status-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
                margin-bottom: 25px;
            }
        }
        
        /* Mycket liten mobil: 1 kolumn */
        @media (max-width: 480px) {
            .status-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .status-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-left: 5px solid #6c757d;
            transition: all 0.3s ease;
        }
        
        .status-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }
        
        .status-card.pump-on {
            border-left-color: #28a745;
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        }
        
        .status-card.alarm {
            border-left-color: #dc3545;
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            animation: pulse-card 2s ease-in-out infinite;
        }
        
        @keyframes pulse-card {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.9; }
        }
        
        .status-card h3 {
            font-size: 14px;
            color: #6c757d;
            text-transform: uppercase;
            margin-bottom: 10px;
            letter-spacing: 1px;
        }
        
        .status-card .value {
            font-size: 36px;
            font-weight: bold;
            color: #2d3748;
        }
        
        .alarm-section {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            display: none;
        }
        
        .alarm-section.visible {
            display: block;
        }
        
        .alarm-section.critical {
            background: #f8d7da;
            border-color: #dc3545;
            animation: pulse-critical 1.5s ease-in-out infinite;
        }
        
        @keyframes pulse-critical {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.01); }
        }
        
        .alarm-section h3 {
            margin-bottom: 15px;
            color: #721c24;
        }
        
        .alarm-item {
            background: white;
            padding: 10px 15px;
            margin: 8px 0;
            border-radius: 6px;
            font-weight: 600;
            color: #721c24;
        }
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        
        /* Mobil: 1 kolumn, mindre gap */
        @media (max-width: 768px) {
            .services-grid {
                grid-template-columns: 1fr;
                gap: 15px;
            }
        }
        
        .service-card {
            background: white;
            border-radius: 12px;
            padding: 0;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            overflow: hidden;
            border: 2px solid transparent;
        }
        
        .service-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 12px 28px rgba(0,0,0,0.15);
            border-color: #667eea;
        }
        
        .service-card.offline {
            opacity: 0.6;
            border-color: #dc3545;
        }
        
        .service-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            text-align: center;
        }
        
        .service-icon {
            font-size: 48px;
            margin-bottom: 10px;
        }
        
        .service-name {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .service-desc {
            font-size: 13px;
            opacity: 0.9;
        }
        
        .service-body {
            padding: 20px;
            text-align: center;
        }
        
        .service-status {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        
        .service-status.online {
            background: #d4edda;
            color: #155724;
        }
        
        .service-status.offline {
            background: #f8d7da;
            color: #721c24;
        }
        
        .open-button {
            display: block;
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.3s ease;
            font-size: 14px;
        }
        
        .open-button:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        /* Mobil: större knappar för fingrar */
        @media (max-width: 768px) {
            .open-button {
                padding: 16px;
                font-size: 16px;
            }
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 13px;
            border-top: 1px solid #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="time-display" id="current-time"></div>
            <img src="/assets/logo" alt="IK Kamp" class="logo">
            <h1>Bevattning Kontrollcentral</h1>
            <div class="subtitle">Fotbollsplan IK Kamp - Central Dashboard</div>
        </div>
        
        <div class="content">
            <!-- Snabb systemstatus -->
            <div class="status-grid" id="status-grid">
                <div class="status-card" id="card-zone">
                    <h3>Aktiv Zon</h3>
                    <div class="value" id="status-zone">-</div>
                </div>
                <div class="status-card" id="card-pump">
                    <h3>Pump Status</h3>
                    <div class="value" id="status-pump">-</div>
                </div>
                <div class="status-card" id="card-mode">
                    <h3>Driftläge</h3>
                    <div class="value" style="font-size: 24px;" id="status-mode">-</div>
                </div>
                <div class="status-card" id="card-alarms">
                    <h3>Larm</h3>
                    <div class="value" id="status-alarms">-</div>
                </div>
            </div>
            
            <!-- Larm-sektion -->
            <div class="alarm-section" id="alarm-section">
                <h3 id="alarm-title">⚠️ Aktiva Larm</h3>
                <div id="alarm-list"></div>
            </div>
            
            <!-- Tjänster -->
            <div class="services-grid">
                <!-- DI Monitor -->
                <div class="service-card" id="service-di">
                    <div class="service-header">
                        <div class="service-icon">🔌</div>
                        <div class="service-name">DI Monitor</div>
                        <div class="service-desc">Digitala Ingångar</div>
                    </div>
                    <div class="service-body">
                        <div class="service-status online" id="status-di">🟢 Online</div>
                        <p style="color: #666; font-size: 13px; margin-bottom: 15px;">
                            Realtidsövervakning av knappar och sensorer. 
                            Uppdateras var 0.5 sekund.
                        </p>
                        <a href="#" onclick="openService(8081); return false;" class="open-button">Öppna DI Monitor</a>
                    </div>
                </div>
                
                <!-- Bevattning API -->
                <div class="service-card" id="service-api">
                    <div class="service-header">
                        <div class="service-icon">💧</div>
                        <div class="service-name">Bevattning API</div>
                        <div class="service-desc">Huvudstyrning</div>
                    </div>
                    <div class="service-body">
                        <div class="service-status online" id="status-api">🟢 Online</div>
                        <p style="color: #666; font-size: 13px; margin-bottom: 15px;">
                            Starta/stoppa zoner, konfigurera system, 
                            sensor-fallback och zonhantering.
                        </p>
                        <a href="#" onclick="openService(8000); return false;" class="open-button">Öppna Styrpanel</a>
                    </div>
                </div>
                
                <!-- Process View -->
                <div class="service-card" id="service-process">
                    <div class="service-header">
                        <div class="service-icon">📊</div>
                        <div class="service-name">Process View</div>
                        <div class="service-desc">Grafisk Övervakning</div>
                    </div>
                    <div class="service-body">
                        <div class="service-status online" id="status-process">🟢 Online</div>
                        <p style="color: #666; font-size: 13px; margin-bottom: 15px;">
                            Visuell fotbollsplan med zonöversikt, 
                            regnprognos och väderdata.
                        </p>
                        <a href="#" onclick="openService(8050); return false;" class="open-button">Öppna Process View</a>
                    </div>
                </div>
                
                <!-- Användarhantering -->
                <div class="service-card" id="service-users">
                    <div class="service-header">
                        <div class="service-icon">👥</div>
                        <div class="service-name">Användarhantering</div>
                        <div class="service-desc">Administration</div>
                    </div>
                    <div class="service-body">
                        <div class="service-status online" id="status-users">🟢 Online</div>
                        <p style="color: #666; font-size: 13px; margin-bottom: 15px;">
                            Skapa och hantera användarkonton. 
                            Kräver superadmin-inloggning.
                        </p>
                        <a href="#" onclick="openService(8082); return false;" class="open-button">Öppna Användarhantering</a>
                    </div>
                </div>
                
                <!-- TODO Checklist -->
                <div class="service-card" id="service-todo">
                    <div class="service-header">
                        <div class="service-icon">📋</div>
                        <div class="service-name">TODO Checklist</div>
                        <div class="service-desc">Projekthantering</div>
                    </div>
                    <div class="service-body">
                        <div class="service-status online" id="status-todo">🟢 Online</div>
                        <p style="color: #666; font-size: 13px; margin-bottom: 15px;">
                            Checklista för installation, tester 
                            och driftsättning av systemet.
                        </p>
                        <a href="#" onclick="openService(8080); return false;" class="open-button">Öppna TODO Lista</a>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Fotbollsplan Bevattning System 2.0</p>
            <p style="margin-top: 5px;">Raspberry Pi + UniPi 1.1 | Uppdateras automatiskt</p>
        </div>
    </div>
    
    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/api/overview');
                const data = await response.json();
                
                if (!data.ok) return;
                
                // Uppdatera systemstatus
                const system = data.system;
                document.getElementById('status-zone').innerText = 
                    system.zone > 0 ? `Zon ${system.zone}` : 'Ingen';
                document.getElementById('status-pump').innerText = 
                    system.pump_on ? '🟢 PÅ' : '⚪ AV';
                document.getElementById('status-mode').innerText = system.mode;
                document.getElementById('status-alarms').innerText = data.alarms.total;
                
                // Uppdatera pump-kort
                const pumpCard = document.getElementById('card-pump');
                if (system.pump_on) {
                    pumpCard.classList.add('pump-on');
                } else {
                    pumpCard.classList.remove('pump-on');
                }
                
                // Uppdatera larm-kort
                const alarmCard = document.getElementById('card-alarms');
                if (data.alarms.total > 0) {
                    alarmCard.classList.add('alarm');
                } else {
                    alarmCard.classList.remove('alarm');
                }
                
                // Visa larm-sektion om det finns larm
                const alarmSection = document.getElementById('alarm-section');
                if (data.alarms.critical.length > 0 || data.alarms.normal.length > 0) {
                    alarmSection.classList.add('visible');
                    
                    if (data.alarms.critical.length > 0) {
                        alarmSection.classList.add('critical');
                        document.getElementById('alarm-title').innerText = '🚨 KRITISKA LARM';
                    } else {
                        alarmSection.classList.remove('critical');
                        document.getElementById('alarm-title').innerText = '⚠️ Aktiva Larm';
                    }
                    
                    let alarmHtml = '';
                    
                    // Kritiska larm först
                    for (const alarm of data.alarms.critical) {
                        alarmHtml += `<div class="alarm-item" style="background: #f8d7da; border-left: 4px solid #dc3545;">
                            🚨 ${alarm.di}: ${alarm.name}
                        </div>`;
                    }
                    
                    // Normala larm
                    for (const alarm of data.alarms.normal) {
                        alarmHtml += `<div class="alarm-item" style="background: #fff3cd; border-left: 4px solid #ffc107;">
                            ⚠️ ${alarm.di}: ${alarm.name}
                        </div>`;
                    }
                    
                    document.getElementById('alarm-list').innerHTML = alarmHtml;
                } else {
                    alarmSection.classList.remove('visible');
                }
                
                // Uppdatera tjänst-status
                for (const [key, online] of Object.entries(data.services)) {
                    const card = document.getElementById(`service-${key}`);
                    const statusEl = document.getElementById(`status-${key}`);
                    
                    if (card && statusEl) {
                        if (online) {
                            card.classList.remove('offline');
                            statusEl.className = 'service-status online';
                            statusEl.innerHTML = '🟢 Online';
                        } else {
                            card.classList.add('offline');
                            statusEl.className = 'service-status offline';
                            statusEl.innerHTML = '🔴 Offline';
                        }
                    }
                }
                
            } catch (error) {
                console.error('Dashboard update error:', error);
            }
        }
        
        function updateTime() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('sv-SE');
            const dateStr = now.toLocaleDateString('sv-SE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
            document.getElementById('current-time').innerHTML = `${dateStr}<br>${timeStr}`;
        }
        
        // Initial load
        updateDashboard();
        updateTime();
        
        // Auto-refresh
        setInterval(updateDashboard, 2000);  // Uppdatera var 2:a sekund
        setInterval(updateTime, 1000);  // Uppdatera tid varje sekund
        
        // Helper function för att öppna tjänster med dynamisk host
        function openService(port) {
            const host = window.location.hostname;
            window.open(`http://${host}:${port}`, '_blank');
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', '8090'))
    print(f"Starting Dashboard Hub on port {port}")
    print(f"Open: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)

