"""
IK Kamp Bevattningskontroll Dashboard med Fotbollsplan
"""

import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime
import requests
import json
import os

# API konfiguration
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "kamp")

# IK Kamp klubbfärger
IK_KAMP_GUL = "#FFD700"
IK_KAMP_BLA = "#003A70"
IK_KAMP_VINROD = "#8B1538"

# Zon-konfiguration enligt skiss
ZONES = {
    1: {"name": "Övre vänster", "x": 20, "y": 20, "color": IK_KAMP_GUL},
    2: {"name": "Övre höger", "x": 60, "y": 20, "color": IK_KAMP_BLA},
    3: {"name": "Mitten vänster", "x": 20, "y": 50, "color": IK_KAMP_VINROD},
    4: {"name": "Mittcirkel", "x": 50, "y": 50, "color": IK_KAMP_GUL},
    5: {"name": "Mitten höger", "x": 80, "y": 50, "color": IK_KAMP_BLA},
    6: {"name": "Nedre vänster", "x": 20, "y": 80, "color": IK_KAMP_VINROD},
    7: {"name": "Nedre höger", "x": 60, "y": 80, "color": IK_KAMP_GUL},
}

# Skapa Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, "/assets/styles.css"])
app.title = "IK Kamp Bevattning"

def get_system_status():
    """Hämta systemstatus från API"""
    try:
        response = requests.get(f"{API_BASE_URL}/status", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {
        "pump_running": False,
        "active_zone": None,
        "valve_states": {},
        "temperature": None,
        "last_update": datetime.now().isoformat()
    }

def get_activity_log():
    """Hämta aktivitetslogg från API"""
    try:
        response = requests.get(f"{API_BASE_URL}/activity-log", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def create_football_field_figure(status):
    """Skapa fotbollsplan med Plotly"""
    active_zone = status.get("active_zone")
    pump_running = status.get("pump_running", False)
    
    fig = go.Figure()
    
    # Gräs bakgrund
    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=100, 
                  fillcolor="#2d5016", line_width=0, layer="below")
    
    # Straffområden
    fig.add_shape(type="rect", x0=5, y0=25, x1=20, y1=75, 
                  fillcolor="rgba(0,0,0,0)", line=dict(color="white", width=1), opacity=0.4)
    fig.add_shape(type="rect", x0=80, y0=25, x1=95, y1=75, 
                  fillcolor="rgba(0,0,0,0)", line=dict(color="white", width=1), opacity=0.4)
    
    # Mittlinje
    fig.add_shape(type="line", x0=50, y0=0, x1=50, y1=100, 
                  line=dict(color="white", width=1), opacity=0.4)
    
    # Mittcirkel
    fig.add_shape(type="circle", x0=35, y0=35, x1=65, y1=65, 
                  fillcolor="rgba(0,0,0,0)", line=dict(color="white", width=1), opacity=0.4)
    
    # Lägg till zoner
    for zone_id, zone_info in ZONES.items():
        is_active = active_zone == zone_id
        size = 16 if is_active else 12
        line_width = 3 if is_active else 1
        
        fig.add_trace(go.Scatter(
            x=[zone_info['x']],
            y=[100 - zone_info['y']],  # Invertera Y för korrekt orientering
            mode='markers+text',
            marker=dict(
                size=size,
                color=zone_info['color'],
                line=dict(color='white', width=line_width),
                opacity=1 if is_active else 0.7
            ),
            text=str(zone_id),
            textfont=dict(color='white', size=14, family='Arial Black'),
            textposition='middle center',
            hovertemplate=f"<b>Zon {zone_id}</b><br>{zone_info['name']}<extra></extra>",
            showlegend=False,
            name=f"Zon {zone_id}"
        ))
    
    # Pump-ikon (mittenövre delen)
    pump_color = IK_KAMP_VINROD if pump_running else "gray"
    fig.add_trace(go.Scatter(
        x=[50],
        y=[95],
        mode='markers+text',
        marker=dict(size=10, color=pump_color, symbol='circle', 
                   line=dict(color='white', width=2)),
        text='⚙' if pump_running else '○',
        textfont=dict(color='white', size=16),
        textposition='middle center',
        hovertemplate="<b>Pump</b><br>" + ("🟢 Körs" if pump_running else "⚪ Stoppad") + "<extra></extra>",
        showlegend=False,
        name="Pump"
    ))
    
    fig.update_layout(
        plot_bgcolor='#2d5016',
        paper_bgcolor='#1a1a1a',
        xaxis=dict(range=[0, 100], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[0, 100], showgrid=False, zeroline=False, visible=False),
        height=600,
        margin=dict(l=20, r=20, t=40, b=20),
        title=dict(
            text="⚽ IK Kamp Fotbollsplan",
            font=dict(color=IK_KAMP_GUL, size=20),
            x=0.5,
            xanchor='center'
        ),
        hovermode='closest'
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False}, id='football-field-graph')

def create_zone_modal():
    """Modal för zonkontroll"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="zone-modal-title")),
        dbc.ModalBody([
            html.Div([
                html.H5("Timer", className="mb-3"),
                dbc.ButtonGroup([
                    dbc.Button("5 min", id="timer-5", color="info", className="timer-btn", n_clicks=0),
                    dbc.Button("10 min", id="timer-10", color="info", className="timer-btn", n_clicks=0),
                    dbc.Button("15 min", id="timer-15", color="info", className="timer-btn", n_clicks=0),
                    dbc.Button("30 min", id="timer-30", color="info", className="timer-btn", n_clicks=0),
                ], className="mb-4 d-flex flex-wrap"),
                html.Hr(),
                html.H5("Direkt kontroll", className="mb-3"),
                dbc.ButtonGroup([
                    dbc.Button("▶ Starta", id="zone-start-btn", color="success", className="action-btn", n_clicks=0),
                    dbc.Button("⏸ Stoppa", id="zone-stop-btn", color="danger", className="action-btn", n_clicks=0),
                ], className="d-flex"),
            ]),
            html.Div(id="zone-action-feedback", className="mt-3")
        ]),
        dbc.ModalFooter(
            dbc.Button("Stäng", id="close-zone-modal", className="ms-auto", n_clicks=0)
        ),
    ], id="zone-modal", is_open=False, centered=True)

def create_activity_log_card(activities):
    """Skapa aktivitetslogg"""
    if not activities:
        return html.Div("Ingen aktivitet ännu", className="text-muted")
    
    items = []
    for activity in activities[:10]:  # Visa senaste 10
        timestamp = activity.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = timestamp
        
        action = activity.get("action", "")
        user = activity.get("user", "System")
        zone = activity.get("zone", "")
        zone_str = f" (Zon {zone})" if zone else ""
        
        items.append(
            html.Div([
                html.Span(time_str, className="text-muted me-2", style={"font-size": "0.85em"}),
                html.Span(f"{action}{zone_str}", className="me-2"),
                html.Span(f"- {user}", className="text-info", style={"font-size": "0.85em"}),
            ], className="mb-1")
        )
    
    return html.Div(items)

# Layout
app.layout = dbc.Container([
    dcc.Interval(id="interval-component", interval=5000, n_intervals=0),  # 5 sekunder
    dcc.Store(id="selected-zone", data=None),
    
    # Header
    dbc.Row([
        dbc.Col([
            html.H1([
                "⚽ IK Kamp Bevattningskontroll",
            ], className="text-center mt-4 mb-2", style={"color": IK_KAMP_GUL}),
            html.P("Fotbollsplan Bromölla", className="text-center text-muted mb-4"),
        ])
    ]),
    
    # Status kort
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Status", className="card-title"),
                    html.Div(id="status-display"),
                ])
            ], className="mb-4")
        ], lg=4, md=6, sm=12),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Nödstopp", className="card-title"),
                    dbc.Button(
                        "🛑 STOPPA ALLT", 
                        id="emergency-stop-btn", 
                        color="danger", 
                        className="w-100 action-btn",
                        n_clicks=0,
                        size="lg"
                    ),
                    html.Div(id="emergency-feedback", className="mt-2")
                ])
            ], className="mb-4")
        ], lg=4, md=6, sm=12),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Senaste aktivitet", className="card-title"),
                    html.Div(id="activity-log-display"),
                ])
            ], className="mb-4", style={"max-height": "200px", "overflow-y": "auto"})
        ], lg=4, md=12, sm=12),
    ]),
    
    # Fotbollsplan
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div(id="football-field"),
                ])
            ])
        ])
    ]),
    
    # Modal
    create_zone_modal(),
    
], fluid=True, className="p-3")

# Callback för att uppdatera status och fotbollsplan
@app.callback(
    [Output("status-display", "children"),
     Output("football-field", "children"),
     Output("activity-log-display", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    status = get_system_status()
    activities = get_activity_log()
    
    # Status display
    pump_status = "🟢 Pump körs" if status.get("pump_running") else "⚪ Pump stoppad"
    active_zone = status.get("active_zone")
    zone_status = f"Aktiv zon: {active_zone}" if active_zone else "Ingen aktiv zon"
    
    status_div = html.Div([
        html.P(pump_status, className="mb-1"),
        html.P(zone_status, className="mb-0"),
    ])
    
    # Fotbollsplan
    field = create_football_field_figure(status)
    
    # Aktivitetslogg
    activity_log = create_activity_log_card(activities)
    
    return status_div, field, activity_log

# Callback för att öppna zon-modal
@app.callback(
    [Output("zone-modal", "is_open"),
     Output("zone-modal-title", "children"),
     Output("selected-zone", "data")],
    [Input({"type": "zone-click", "zone": dash.dependencies.ALL}, "n_clicks"),
     Input("close-zone-modal", "n_clicks")],
    [State("zone-modal", "is_open"),
     State("selected-zone", "data")]
)
def toggle_zone_modal(zone_clicks, close_clicks, is_open, selected_zone):
    ctx = callback_context
    
    if not ctx.triggered:
        return False, "", None
    
    trigger_id = ctx.triggered[0]["prop_id"]
    
    # Stäng modal
    if "close-zone-modal" in trigger_id:
        return False, "", None
    
    # Öppna för specifik zon (implementeras vid behov med JavaScript)
    return is_open, f"Zon {selected_zone or '?'}", selected_zone

# Callback för zonstart
@app.callback(
    Output("zone-action-feedback", "children"),
    [Input("zone-start-btn", "n_clicks"),
     Input("timer-5", "n_clicks"),
     Input("timer-10", "n_clicks"),
     Input("timer-15", "n_clicks"),
     Input("timer-30", "n_clicks")],
    [State("selected-zone", "data")]
)
def handle_zone_start(start_clicks, timer5, timer10, timer15, timer30, zone):
    ctx = callback_context
    
    if not ctx.triggered or not zone:
        return ""
    
    trigger_id = ctx.triggered[0]["prop_id"]
    
    # Direkt start
    if "zone-start-btn" in trigger_id and start_clicks:
        try:
            response = requests.post(
                f"{API_BASE_URL}/command/manual",
                json={"zone": zone, "duration": 600, "user": "admin"},
                headers={"X-API-Key": API_KEY},
                timeout=5
            )
            if response.status_code == 200:
                return dbc.Alert("✅ Zon startad!", color="success", duration=3000)
            else:
                return dbc.Alert("❌ Fel vid start", color="danger", duration=3000)
        except Exception as e:
            return dbc.Alert(f"❌ Fel: {str(e)}", color="danger", duration=3000)
    
    # Timer-start
    duration_map = {
        "timer-5": 5,
        "timer-10": 10,
        "timer-15": 15,
        "timer-30": 30
    }
    
    for btn_id, minutes in duration_map.items():
        if btn_id in trigger_id:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/command/manual",
                    json={"zone": zone, "duration": minutes * 60, "user": "admin"},
                    headers={"X-API-Key": API_KEY},
                    timeout=5
                )
                if response.status_code == 200:
                    return dbc.Alert(f"✅ Zon startad för {minutes} min!", color="success", duration=3000)
                else:
                    return dbc.Alert("❌ Fel vid start", color="danger", duration=3000)
            except Exception as e:
                return dbc.Alert(f"❌ Fel: {str(e)}", color="danger", duration=3000)
    
    return ""

# Callback för zonstopp
@app.callback(
    Output("zone-action-feedback", "children", allow_duplicate=True),
    [Input("zone-stop-btn", "n_clicks")],
    [State("selected-zone", "data")],
    prevent_initial_call=True
)
def handle_zone_stop(stop_clicks, zone):
    if not stop_clicks or not zone:
        return ""
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/command/stop",
            json={"user": "admin"},
            headers={"X-API-Key": API_KEY},
            timeout=5
        )
        if response.status_code == 200:
            return dbc.Alert("⏸ Zon stoppad!", color="info", duration=3000)
        else:
            return dbc.Alert("❌ Fel vid stopp", color="danger", duration=3000)
    except Exception as e:
        return dbc.Alert(f"❌ Fel: {str(e)}", color="danger", duration=3000)

# Callback för nödstopp
@app.callback(
    Output("emergency-feedback", "children"),
    [Input("emergency-stop-btn", "n_clicks")],
    prevent_initial_call=True
)
def handle_emergency_stop(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/command/stop",
            json={"user": "admin"},
            headers={"X-API-Key": API_KEY},
            timeout=5
        )
        if response.status_code == 200:
            return dbc.Alert("🛑 NÖDSTOPP AKTIVERAT!", color="warning", duration=4000)
        else:
            return dbc.Alert("❌ Fel vid nödstopp", color="danger", duration=3000)
    except Exception as e:
        return dbc.Alert(f"❌ Fel: {str(e)}", color="danger", duration=3000)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
