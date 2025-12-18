#!/usr/bin/env python3
"""
Plotly Dash Process View för Fotbollsplan Bevattning
Grafisk visualisering av bevattningssystemet med:
- Zonsstatus och kontroll
- Pumpstatus
- Regnprognos och historik
- Felvisualisering
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, List

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
from dotenv import load_dotenv
import requests

load_dotenv()

# Konfiguration
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "change-me")
DASH_PORT = int(os.getenv("DASH_PORT", "8050"))
DASH_HOST = os.getenv("DASH_HOST", "0.0.0.0")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dash app
app = dash.Dash(
    __name__,
    title="Bevattning Process View",
    update_title="Uppdaterar...",
    assets_folder='assets'
)

# Färgschema
COLORS = {
    'background': '#f5f5f5',
    'card': '#ffffff',
    'primary': '#4CAF50',
    'danger': '#f44336',
    'warning': '#ff9800',
    'info': '#2196F3',
    'text': '#333333',
    'zone_active': '#4CAF50',
    'zone_inactive': '#e0e0e0',
    'pump_on': '#2196F3',
    'pump_off': '#9e9e9e',
    'error': '#f44336'
}

# Ikoner (emoji som fallback, SVG laddas från assets)
ICONS = {
    'pump_on': '💧',
    'pump_off': '⚫',
    'zone_active': '🟢',
    'zone_inactive': '⚪',
    'zone_selected': '🟡',
    'rain': '🌧️',
    'moisture': '💧',
    'temperature': '🌡️',
    'error': '🔴',
    'warning': '⚠️',
    'success': '✅',
    'sequence': '📋'
}


def make_api_request(endpoint: str, method: str = "GET", json_data: Dict = None) -> Dict[str, Any]:
    """Gör API-anrop med felhantering"""
    url = f"{API_URL}{endpoint}"
    headers = {"X-API-Key": API_KEY}
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=json_data or {}, timeout=10)
        else:
            return {"ok": False, "error": f"Unsupported method: {method}"}
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"ok": False, "error": str(e)}


def create_zone_figure(zones_data: List[Dict]) -> go.Figure:
    """Skapa grafisk representation av zoner med klickbar funktionalitet"""
    fig = go.Figure()
    
    # Skapa ett rutnät med zoner
    zone_positions = {
        1: (0, 2), 2: (1, 2), 3: (2, 2),  # Övre raden (center)
        4: (0, 1), 5: (1, 1), 6: (2, 1), 7: (1, 0)  # Nedre raderna (horn)
    }
    
    for zone_data in zones_data:
        zone_num = zone_data['zone']
        x, y = zone_positions.get(zone_num, (0, 0))
        
        # Färg baserat på status
        if zone_data['active']:
            color = COLORS['zone_active']
            text_color = 'white'
            size = 100
            status_text = 'Aktiv'
        elif zone_data['selected']:
            color = COLORS['warning']
            text_color = 'white'
            size = 90
            status_text = 'Vald'
        else:
            color = COLORS['zone_inactive']
            text_color = COLORS['text']
            size = 80
            status_text = 'Inaktiv'
        
        # Lägg till zon som cirkel med klickbar data
        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode='markers+text',
            marker=dict(size=size, color=color, line=dict(width=2, color='#333')),
            text=f"Zon {zone_num}",
            textposition="middle center",
            textfont=dict(size=14, color=text_color, family='Arial Black'),
            name=f"Zon {zone_num}",
            customdata=[zone_num],  # Store zone number for click handling
            hovertemplate=f"<b>Zon {zone_num}</b><br>"
                         f"Status: {status_text}<br>"
                         f"<i>Klicka för att starta/stoppa</i><br>"
                         "<extra></extra>"
        ))
    
    # Layout
    fig.update_layout(
        showlegend=False,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['card'],
        xaxis=dict(showgrid=False, showticklabels=False, range=[-0.5, 2.5]),
        yaxis=dict(showgrid=False, showticklabels=False, range=[-0.5, 2.5]),
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        title=dict(text="Zonöversikt - Klicka på en zon för att starta", x=0.5, xanchor='center'),
        clickmode='event+select'  # Enable click events
    )
    
    return fig


def create_rain_forecast_figure(rain_data: Dict) -> go.Figure:
    """Skapa regnprognosgraf"""
    if not rain_data or not rain_data.get('ok'):
        return go.Figure().add_annotation(
            text="Ingen regndata tillgänglig",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    forecast = rain_data.get('forecast_24h', {})
    hourly = forecast.get('hourly', [])
    
    if not hourly:
        return go.Figure().add_annotation(
            text="Ingen prognos tillgänglig",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Parse timestamps with error handling
    times = []
    precip = []
    for h in hourly:
        try:
            time_str = h['time']
            # Handle ISO format timestamps with or without 'Z' suffix
            if time_str.endswith('Z'):
                time_str = time_str[:-1] + '+00:00'
            times.append(datetime.fromisoformat(time_str))
            precip.append(h['precipitation'])
        except (ValueError, KeyError, AttributeError) as e:
            logger.warning(f"Kunde inte tolka tidsstämpel: {e}")
            continue
    
    if not times:
        return go.Figure().add_annotation(
            text="Kunde inte tolka prognosdata",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=times,
        y=precip,
        name='Nederbörd',
        marker_color=COLORS['info']
    ))
    
    fig.update_layout(
        title=f"Regnprognos 24h (Total: {forecast.get('total_mm', 0):.1f} mm)",
        xaxis_title="Tid",
        yaxis_title="Nederbörd (mm)",
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['card'],
        height=300,
        margin=dict(l=50, r=20, t=40, b=40)
    )
    
    return fig


def create_rain_history_figure(rain_data: Dict) -> go.Figure:
    """Skapa historisk regngraf"""
    if not rain_data or not rain_data.get('ok'):
        return go.Figure().add_annotation(
            text="Ingen historisk data tillgänglig",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    history = rain_data.get('history_7d', {})
    daily = history.get('daily', [])
    
    if not daily:
        return go.Figure().add_annotation(
            text="Ingen historik tillgänglig",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    dates = [d['date'] for d in daily]
    precip = [d['precipitation'] for d in daily]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates,
        y=precip,
        name='Nederbörd',
        marker_color=COLORS['primary']
    ))
    
    total_rain = sum(precip)
    fig.update_layout(
        title=f"Regn senaste 7 dagarna (Total: {total_rain:.1f} mm)",
        xaxis_title="Datum",
        yaxis_title="Nederbörd (mm)",
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['card'],
        height=300,
        margin=dict(l=50, r=20, t=40, b=40)
    )
    
    return fig


# Layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Bevattning Process View", style={'color': 'white', 'textAlign': 'center', 'margin': '0'}),
        html.P("Live övervakning och styrning av bevattningssystemet", 
               style={'color': 'white', 'textAlign': 'center', 'margin': '0'})
    ], style={
        'backgroundColor': COLORS['primary'],
        'padding': '20px',
        'marginBottom': '20px'
    }),
    
    # Main content
    html.Div([
        # Vänster kolumn - Process view
        html.Div([
            # Zonöversikt
            html.Div([
                dcc.Graph(id='zone-graph', config={'displayModeBar': False})
            ], style={
                'backgroundColor': COLORS['card'],
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'marginBottom': '20px'
            }),
            
            # Pumpstatus och kontroller
            html.Div([
                html.H3("Pump & Kontroller", style={'marginTop': '0'}),
                html.Div(id='pump-status', style={'fontSize': '18px', 'marginBottom': '15px'}),
                html.Div(id='sequence-status', style={'fontSize': '14px', 'marginBottom': '15px'}),
                
                html.Div([
                    html.Label("Välj zon:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='zone-selector',
                        options=[{'label': f'Zon {i}', 'value': i} for i in range(1, 8)],
                        value=1,
                        style={'width': '150px', 'display': 'inline-block'}
                    ),
                ], style={'marginBottom': '15px'}),
                
                html.Div([
                    html.Button('Starta Zon', id='btn-start-zone', n_clicks=0,
                               style={'marginRight': '10px', 'padding': '10px 20px',
                                     'backgroundColor': COLORS['primary'], 'color': 'white',
                                     'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'}),
                    html.Button('Stoppa', id='btn-stop', n_clicks=0,
                               style={'padding': '10px 20px', 'backgroundColor': COLORS['danger'],
                                     'color': 'white', 'border': 'none', 'borderRadius': '4px',
                                     'cursor': 'pointer'}),
                ]),
                
                html.Div(id='control-feedback', style={'marginTop': '15px', 'padding': '10px',
                                                       'borderRadius': '4px', 'display': 'none'})
            ], style={
                'backgroundColor': COLORS['card'],
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'marginBottom': '20px'
            }),
            
            # Felstatus
            html.Div([
                html.H3("Systemstatus & Fel", style={'marginTop': '0'}),
                html.Div(id='error-status')
            ], style={
                'backgroundColor': COLORS['card'],
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            })
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        # Höger kolumn - Väderdata
        html.Div([
            # Regnprognos
            html.Div([
                dcc.Graph(id='rain-forecast-graph', config={'displayModeBar': False})
            ], style={
                'backgroundColor': COLORS['card'],
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'marginBottom': '20px'
            }),
            
            # Historisk regn
            html.Div([
                dcc.Graph(id='rain-history-graph', config={'displayModeBar': False})
            ], style={
                'backgroundColor': COLORS['card'],
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'marginBottom': '20px'
            }),
            
            # Miljödata
            html.Div([
                html.H3("Miljödata", style={'marginTop': '0'}),
                html.Div(id='environment-data')
            ], style={
                'backgroundColor': COLORS['card'],
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            })
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top',
                 'marginLeft': '4%'})
    ], style={'padding': '20px', 'maxWidth': '1400px', 'margin': '0 auto'}),
    
    # Auto-uppdatering intervall (5 sekunder)
    dcc.Interval(id='interval-update', interval=5000, n_intervals=0),
    
    # Hidden div för att lagra data
    html.Div(id='hidden-process-data', style={'display': 'none'}),
    html.Div(id='hidden-rain-data', style={'display': 'none'}),
    html.Div(id='hidden-zone-click-result', style={'display': 'none'})  # Store zone click results
], style={'backgroundColor': COLORS['background'], 'minHeight': '100vh'})


# Callbacks
@app.callback(
    [Output('hidden-process-data', 'children'),
     Output('hidden-rain-data', 'children')],
    [Input('interval-update', 'n_intervals')]
)
def update_data(n):
    """Hämta data från API"""
    
    process_data = make_api_request("/process-view")
    rain_data = make_api_request("/rain-forecast")
    
    return json.dumps(process_data), json.dumps(rain_data)


@app.callback(
    Output('zone-graph', 'figure'),
    [Input('hidden-process-data', 'children')]
)
def update_zone_graph(process_json):
    """Uppdatera zongraf"""
    
    if not process_json:
        return go.Figure()
    
    try:
        data = json.loads(process_json)
        if data.get('ok') and 'zones' in data:
            return create_zone_figure(data['zones'])
    except Exception as e:
        logger.error(f"Error updating zone graph: {e}")
    
    return go.Figure()


@app.callback(
    Output('pump-status', 'children'),
    [Input('hidden-process-data', 'children')]
)
def update_pump_status(process_json):
    """Uppdatera pumpstatus"""
    
    if not process_json:
        return "Laddar..."
    
    try:
        data = json.loads(process_json)
        if data.get('ok') and 'pump' in data:
            pump = data['pump']
            color = COLORS['pump_on'] if pump['on'] else COLORS['pump_off']
            icon = ICONS['pump_on'] if pump['on'] else ICONS['pump_off']
            
            return html.Div([
                html.Span(icon, style={'fontSize': '24px', 'marginRight': '10px'}),
                html.Span(f"Pump: {pump['status']}", 
                         style={'fontWeight': 'bold', 'color': color})
            ])
    except Exception as e:
        logger.error(f"Error updating pump status: {e}")
    
    return "Fel vid hämtning av pumpstatus"


@app.callback(
    Output('sequence-status', 'children'),
    [Input('hidden-process-data', 'children')]
)
def update_sequence_status(process_json):
    """Uppdatera sekvensstatus"""
    
    if not process_json:
        return ""
    
    try:
        data = json.loads(process_json)
        if data.get('ok') and 'sequence' in data:
            seq = data['sequence']
            if seq['active']:
                return html.Div([
                    html.Span(ICONS['sequence'] + " ", style={'fontSize': '18px'}),
                    html.Span(f"Sekvens aktiv - Steg {seq['current_step']}, Zon {seq['current_zone']}")
                ], style={'color': COLORS['info']})
            else:
                return html.Div("Ingen sekvens aktiv", style={'color': '#666'})
    except Exception as e:
        logger.error(f"Error updating sequence status: {e}")
    
    return ""


@app.callback(
    Output('error-status', 'children'),
    [Input('hidden-process-data', 'children')]
)
def update_error_status(process_json):
    """Uppdatera felstatus med detaljerade förklaringar"""
    
    if not process_json:
        return "Laddar..."
    
    try:
        data = json.loads(process_json)
        if data.get('ok'):
            error_details = data.get('error_details', {})
            block = data.get('block_status', {})
            
            error_items = []
            
            # Visa detaljerade felmeddelanden
            severity_order = ['critical', 'warning', 'info']
            severity_colors = {
                'critical': COLORS['error'],
                'warning': COLORS['warning'],
                'info': COLORS['info']
            }
            severity_bg = {
                'critical': '#ffebee',
                'warning': '#fff3e0',
                'info': '#e3f2fd'
            }
            
            # Samla alla aktiva fel
            active_errors = []
            for error_key, error_info in error_details.items():
                if error_info.get('active'):
                    active_errors.append(error_info)
            
            # Sortera efter allvarlighetsgrad
            active_errors.sort(key=lambda x: severity_order.index(x.get('severity', 'info')))
            
            # Visa aktiva fel med förklaringar
            for error_info in active_errors:
                severity = error_info.get('severity', 'info')
                error_items.append(html.Div([
                    html.Div([
                        html.Span(ICONS.get('error' if severity == 'critical' else 'warning', '⚠️') + " ", 
                                 style={'fontSize': '18px'}),
                        html.Span(error_info.get('text', 'Okänt fel'), 
                                 style={'fontWeight': 'bold'})
                    ], style={'marginBottom': '5px'}),
                    html.Div(error_info.get('explanation', ''),
                            style={'fontSize': '13px', 'marginLeft': '25px', 'color': '#555'})
                ], style={
                    'color': severity_colors.get(severity, COLORS['text']),
                    'marginBottom': '10px',
                    'padding': '10px',
                    'backgroundColor': severity_bg.get(severity, '#f5f5f5'),
                    'borderRadius': '4px',
                    'borderLeft': f'4px solid {severity_colors.get(severity, COLORS["text"])}'
                }))
            
            # Block status med förklaring
            if block.get('blocked'):
                error_items.append(html.Div([
                    html.Div([
                        html.Span("🚫 ", style={'fontSize': '18px'}),
                        html.Span(f"Blockering: {block.get('text', 'Okänt')}",
                                 style={'fontWeight': 'bold'})
                    ], style={'marginBottom': '5px'}),
                    html.Div(block.get('explanation', 'Ingen förklaring tillgänglig'),
                            style={'fontSize': '13px', 'marginLeft': '25px', 'color': '#555'})
                ], style={
                    'color': COLORS['danger'],
                    'marginTop': '15px',
                    'padding': '10px',
                    'backgroundColor': '#ffebee',
                    'borderRadius': '4px',
                    'borderLeft': f'4px solid {COLORS["danger"]}'
                }))
            
            # Om inga fel finns
            if not active_errors and not block.get('blocked'):
                error_items.append(html.Div([
                    html.Span(ICONS['success'] + " ", style={'fontSize': '20px'}),
                    html.Span("Systemet OK", style={'fontWeight': 'bold', 'fontSize': '16px'}),
                    html.Div("Inga aktiva fel eller blockeringar.",
                            style={'fontSize': '13px', 'marginTop': '5px', 'color': '#555'})
                ], style={
                    'color': COLORS['primary'],
                    'padding': '15px',
                    'backgroundColor': '#e8f5e9',
                    'borderRadius': '4px',
                    'borderLeft': f'4px solid {COLORS["primary"]}'
                }))
            
            
            return error_items
    except Exception as e:
        logger.error(f"Error updating error status: {e}")
    
    return "Fel vid hämtning av felstatus"


@app.callback(
    Output('rain-forecast-graph', 'figure'),
    [Input('hidden-rain-data', 'children')]
)
def update_rain_forecast(rain_json):
    """Uppdatera regnprognosgraf"""
    
    if not rain_json:
        return go.Figure()
    
    try:
        data = json.loads(rain_json)
        return create_rain_forecast_figure(data)
    except Exception as e:
        logger.error(f"Error updating rain forecast: {e}")
    
    return go.Figure()


@app.callback(
    Output('rain-history-graph', 'figure'),
    [Input('hidden-rain-data', 'children')]
)
def update_rain_history(rain_json):
    """Uppdatera historisk regngraf"""
    
    if not rain_json:
        return go.Figure()
    
    try:
        data = json.loads(rain_json)
        return create_rain_history_figure(data)
    except Exception as e:
        logger.error(f"Error updating rain history: {e}")
    
    return go.Figure()


@app.callback(
    Output('environment-data', 'children'),
    [Input('hidden-process-data', 'children')]
)
def update_environment_data(process_json):
    """Uppdatera miljödata"""
    
    if not process_json:
        return "Laddar..."
    
    try:
        data = json.loads(process_json)
        if data.get('ok') and 'environment' in data:
            env = data['environment']
            config = data.get('configuration', {})
            
            return html.Div([
                html.Div([
                    html.Span(ICONS['moisture'] + " Markfukt: ", style={'fontWeight': 'bold'}),
                    html.Span(f"{env.get('moisture_percent', 0)}%")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span(ICONS['rain'] + " Regn 24h: ", style={'fontWeight': 'bold'}),
                    html.Span(f"{env.get('rain_24h_mm', 0)} mm")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span(ICONS['temperature'] + " Temperatur: ", style={'fontWeight': 'bold'}),
                    html.Span(f"{env.get('temperature_c', 0)}°C")
                ], style={'marginBottom': '15px'}),
                html.Hr(),
                html.Div([
                    html.Span("⏱️ Tid Center: ", style={'fontWeight': 'bold'}),
                    html.Span(f"{config.get('tid_center_min', 0)} min")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span("⏱️ Tid Horn: ", style={'fontWeight': 'bold'}),
                    html.Span(f"{config.get('tid_horn_min', 0)} min")
                ])
            ])
    except Exception as e:
        logger.error(f"Error updating environment data: {e}")
    
    return "Fel vid hämtning av miljödata"


@app.callback(
    [Output('control-feedback', 'children'),
     Output('control-feedback', 'style')],
    [Input('btn-start-zone', 'n_clicks'),
     Input('btn-stop', 'n_clicks')],
    [State('zone-selector', 'value')]
)
def handle_controls(start_clicks, stop_clicks, selected_zone):
    """Hantera kontrollknappar"""
    ctx = callback_context
    
    if not ctx.triggered:
        return "", {'display': 'none'}
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'btn-start-zone':
        result = make_api_request(
            "/zone-control",
            method="POST",
            json_data={"zone": selected_zone, "action": "start"}
        )
        
        if result.get('ok'):
            return (
                html.Div([
                    html.Span(ICONS['success'] + " ", style={'fontSize': '18px'}),
                    html.Span(result.get('message', f"Zon {selected_zone} startad"))
                ]),
                {'display': 'block', 'backgroundColor': '#d4edda', 'color': '#155724',
                 'border': '1px solid #c3e6cb', 'marginTop': '15px', 'padding': '10px',
                 'borderRadius': '4px'}
            )
        else:
            return (
                html.Div([
                    html.Span(ICONS['error'] + " ", style={'fontSize': '18px'}),
                    html.Span(f"Fel: {result.get('error', 'Okänt fel')}")
                ]),
                {'display': 'block', 'backgroundColor': '#f8d7da', 'color': '#721c24',
                 'border': '1px solid #f5c6cb', 'marginTop': '15px', 'padding': '10px',
                 'borderRadius': '4px'}
            )
    
    elif button_id == 'btn-stop':
        result = make_api_request(
            "/zone-control",
            method="POST",
            json_data={"zone": 1, "action": "stop"}  # Zone doesn't matter for stop
        )
        
        if result.get('ok'):
            return (
                html.Div([
                    html.Span(ICONS['success'] + " ", style={'fontSize': '18px'}),
                    html.Span("Bevattning stoppad")
                ]),
                {'display': 'block', 'backgroundColor': '#d4edda', 'color': '#155724',
                 'border': '1px solid #c3e6cb', 'marginTop': '15px', 'padding': '10px',
                 'borderRadius': '4px'}
            )
        else:
            return (
                html.Div([
                    html.Span(ICONS['error'] + " ", style={'fontSize': '18px'}),
                    html.Span(f"Fel: {result.get('error', 'Okänt fel')}")
                ]),
                {'display': 'block', 'backgroundColor': '#f8d7da', 'color': '#721c24',
                 'border': '1px solid #f5c6cb', 'marginTop': '15px', 'padding': '10px',
                 'borderRadius': '4px'}
            )
    
    return "", {'display': 'none'}


@app.callback(
    [Output('control-feedback', 'children', allow_duplicate=True),
     Output('control-feedback', 'style', allow_duplicate=True)],
    [Input('zone-graph', 'clickData')],
    [State('hidden-process-data', 'children')],
    prevent_initial_call=True
)
def handle_zone_click(clickData, process_json):
    """Hantera klick på zoner i grafen"""
    
    if not clickData or not clickData.get('points'):
        return "", {'display': 'none'}
    
    try:
        # Extract zone number from clicked point
        point = clickData['points'][0]
        zone_num = point.get('customdata')
        
        if not zone_num or not isinstance(zone_num, (int, list)):
            return "", {'display': 'none'}
        
        # If customdata is a list, get first element
        if isinstance(zone_num, list):
            zone_num = zone_num[0] if zone_num else None
        
        if zone_num is None:
            return "", {'display': 'none'}
        
        # Check if zone is currently active
        is_active = False
        if process_json:
            try:
                data = json.loads(process_json)
                if data.get('ok') and 'zones' in data:
                    for zone_data in data['zones']:
                        if zone_data['zone'] == zone_num and zone_data['active']:
                            is_active = True
                            break
            except Exception as e:
                logger.error(f"Error parsing process data for zone click: {e}")
        
        # If active, stop; otherwise start
        action = "stop" if is_active else "start"
        
        result = make_api_request(
            "/zone-control",
            method="POST",
            json_data={"zone": zone_num, "action": action}
        )
        
        if result.get('ok'):
            message = f"Zon {zone_num} stoppad" if action == "stop" else f"Zon {zone_num} startad"
            return (
                html.Div([
                    html.Span(ICONS['success'] + " ", style={'fontSize': '18px'}),
                    html.Span(message)
                ]),
                {'display': 'block', 'backgroundColor': '#d4edda', 'color': '#155724',
                 'border': '1px solid #c3e6cb', 'marginTop': '15px', 'padding': '10px',
                 'borderRadius': '4px'}
            )
        else:
            return (
                html.Div([
                    html.Span(ICONS['error'] + " ", style={'fontSize': '18px'}),
                    html.Span(f"Fel: {result.get('error', 'Okänt fel')}")
                ]),
                {'display': 'block', 'backgroundColor': '#f8d7da', 'color': '#721c24',
                 'border': '1px solid #f5c6cb', 'marginTop': '15px', 'padding': '10px',
                 'borderRadius': '4px'}
            )
    
    except Exception as e:
        logger.error(f"Error handling zone click: {e}")
        return (
            html.Div([
                html.Span(ICONS['error'] + " ", style={'fontSize': '18px'}),
                html.Span(f"Fel vid zonklick: {str(e)}")
            ]),
            {'display': 'block', 'backgroundColor': '#f8d7da', 'color': '#721c24',
             'border': '1px solid #f5c6cb', 'marginTop': '15px', 'padding': '10px',
             'borderRadius': '4px'}
        )


if __name__ == '__main__':
    logger.info(f"Starting Dash app on {DASH_HOST}:{DASH_PORT}")
    logger.info(f"API URL: {API_URL}")
    app.run_server(host=DASH_HOST, port=DASH_PORT, debug=False)
