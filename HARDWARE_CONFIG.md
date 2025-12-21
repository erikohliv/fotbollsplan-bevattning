# Hardware Configuration - Fotbollsplan Bevattning

## Översikt

Filen `hardware_config.json` innehåller en komplett specifikation av bevattningssystemets hårdvara, inklusive pump, ventiler, rör och alla 7 zoner med beräknade tryck och flöden.

## Syfte

Denna konfigurationsfil är designad för att:
1. **Dokumentera as-built hårdvaruspecifikationer** efter installationen 2025
2. **Ge GitHub Copilot kontext** om systemets begränsningar och konfiguration
3. **Underlätta felsökning och underhåll** genom att samla all hårdvarudata på ett ställe
4. **Identifiera problemzoner** och ge rekommendationer för uppgraderingar

## Struktur

### Project Meta
- Projektnamn och beskrivning
- Instruktioner för GitHub Copilot
- Senaste uppdateringsdatum

### Pump Station
Specifikationer för huvudpumpen **E.M.S. DX 12-40T**:
- Effekt: 4.0 kW
- Max tryckhöjd: 116 meter
- Max flöde: 250 l/min
- **Kritisk begränsning:** Genererar mycket högt tryck (>10 bar) vid låga flöden (<100 l/min)

### Component Catalog
Katalog över tillgängliga komponenter:

#### Ventiler
- **V_STD (Standard):** Hunter PGV 1½ - Tryckfall 0.27 bar
- **V_FC (Flow Control):** Hunter PGV 1½ FC - Variabelt tryckfall, kan reducera nedströmstryck manuellt

#### Rör
- Huvudslinga: PEM 75 PN16 (ny)
- Center lateraler: PEM 63 (befintlig)
- Hörn lateraler: PEM 32/40 (befintlig)

### Zones (7 st)

#### Center-zoner (1-3) - OPTIMAL STATUS
- **Zoner:** 1 (Center Top), 2 (Center Middle), 3 (Center Bottom)
- **Spridare:** Hunter I-90 (1 st per zon)
- **Flöde:** 180 l/min per zon
- **Tryck:** 7.0-7.2 bar
- **Status:** OPTIMAL - Tryck och flöde inom specifikation

#### Hörn-zoner (4-7) - HÖGTRYCKSVARNING
- **Zoner:** 4 (Corner Top Right), 5 (Corner Bottom Right), 6 (Corner Top Left), 7 (Corner Bottom Left)
- **Spridare:** Hunter I-25 (2 st per zon)
- **Flöde:** 90 l/min per zon (under pumpens optimala område)
- **Tryck:** 10.5 bar (över rekommenderat)
- **Status:** ⚠️ WARNING: HIGH PRESSURE (>10 bar). Pump operating near shut-off head.

## Problem och Lösning

### Problem: Högt tryck i hörnzoner
Hörnzonerna (4-7) har endast 90 l/min flöde, vilket är betydligt lägre än pumpens optimala arbetspunkt. Detta gör att pumpen arbetar nära sin stängningshöjd (shut-off head) och genererar över 10 bar tryck.

**Risker:**
- Överstress på spridare och rör
- Risk för läckage
- Reducerad livslängd på komponenter
- Potentiell skada på spridarhuvuden

### Lösning: Flow Control ventiler
Byt ut standardventiler (V_STD) mot Flow Control-ventiler (V_FC) i de 4 hörnzonerna. Flow Control-ventilerna kan ställas in manuellt för att:
- Reducera nedströmstrycket till säkra nivåer
- Bibehålla korrekt flöde till spridarna
- Skydda systemet från överbelastning

**Implementering:**
När en ventil i `hardware_config.json` ändras från `"valve_installed": "V_STD"` till `"valve_installed": "V_FC"`, ska statusen uppdateras från varning till optimal.

## Användning i Kod

Se `example_hardware_config_usage.py` för exempel på hur konfigurationen används i Python-kod.

### Grundläggande användning:
```python
import json

# Ladda konfiguration
with open('hardware_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Hämta pump-info
pump = config['pump_station']
print(f"Pump: {pump['model']}, {pump['specs']['power_kw']} kW")

# Lista alla zoner
for zone in config['zones']:
    print(f"Zone {zone['zone_id']}: {zone['location']} - {zone['status']}")

# Hitta högtryckszoner
high_pressure = [z for z in config['zones'] if z['estimated_pressure_bar'] > 10]
print(f"High pressure zones: {len(high_pressure)}")
```

## GitHub Copilot Integration

Filen innehåller instruktioner för GitHub Copilot i `project_meta.instructions_for_copilot`:

> "Use this file to answer technical questions. If a valve is changed to a 'Flow Control' type in the 'zones' list, assume the high pressure warning is resolved."

Detta gör att Copilot automatiskt kan:
- Förstå systemets begränsningar
- Ge korrekta råd om ventiluppgraderingar
- Identifiera problemzoner
- Validera förändringar mot hårdvaruspecifikationer

## Underhåll

### När ska filen uppdateras?
- Efter installation av nya komponenter
- När ventiler byts ut (t.ex. V_STD → V_FC)
- Vid ändringar i zonkonfiguration
- Efter tryckmätningar som visar nya värden
- Vid uppgradering av pump eller huvudsystem

### Versionshantering
- Uppdatera `last_updated` fältet när ändringar görs
- Dokumentera ändringar i git commit-meddelanden
- Behåll gamla versioner via git historik

## Relaterade Filer

- `README.md` - Huvuddokumentation med installation och användning
- `.github/copilot-instructions.md` - GitHub Copilot instruktioner
- `example_hardware_config_usage.py` - Exempel på användning av konfigurationen
- `api_main.py` - FastAPI backend som kan utökas att använda denna config
- `bevattning_controller.py` - Python controller för väderdata och styrning

## Support

För frågor eller problem relaterade till hårdvarukonfigurationen, kontakta systemansvarig eller se dokumentationen i respektive Python-modul.
