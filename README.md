# Fotbollsplan bevattning

## Arkitektur
- **PLC (ST):** Säker/sekvenslogik, anti-vattenslag, E-stop, zonbyte.
- **Python controller:** Hämtar Open-Meteo, markfukt (valfritt), skriver Modbus-register, pulserar start.
- **FastAPI-backend:** API/Webb-UI + Modbus-brygga. Skyddas med API-nyckel.
- **Display Manager:** Hanterar två I2C LCD-displayer för status och manuell styrning.
- **Hårdvara:** UNIPI 1.1, Raspberry Pi 3 (Debian Bookworm). Pump_enable styr Siemens LOGO → VFD (mjukstart).

## Installation på Raspberry Pi

### Komplett installation (Rekommenderat för nya system)
För helt ny installation på Raspberry Pi 4 med Debian Bookworm Lite:

**Steg 1: Grundläggande förberedelser**
```bash
sudo apt update
sudo apt install -y python3 git
git clone https://github.com/erikohliv/fotbollsplan-bevattning.git
cd fotbollsplan-bevattning
```

**Steg 2: Kör komplett installation**
```bash
sudo python3 install_complete.py
```

Det kompletta installationsskriptet guidar dig genom:
- **WiFi-sökning och konfiguration** - Sök och anslut till rätt nätverk
- Systempaket-installation (Python, I2C-verktyg, nätverksverktyg)
- I2C-aktivering för LCD-displayer
- Python virtual environment och beroenden
- Miljövariabel-konfiguration (API-nyckel, Modbus, SMTP)
- Tailscale installation och konfiguration (valfritt för fjärråtkomst)
- systemd-tjänster installation och aktivering
- Automatisk omstart för att aktivera alla ändringar

Efter installationen är systemet helt klart att använda!

### Snabbstart med setup.py (För befintliga system)
Om systemet redan har grundläggande paket installerade:
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip i2c-tools python3-smbus
git clone https://github.com/erikohliv/fotbollsplan-bevattning.git
cd fotbollsplan-bevattning
python3 setup.py
```

Setup-scriptet guidar dig genom:
- Konfiguration av API-nyckel och Modbus-inställningar (IP, port, unit ID)
- Automatisk installation av Python-beroenden
- Valfri installation och konfiguration av Tailscale för fjärråtkomst
- Firewall-konfiguration för Tailscale (om ufw är tillgängligt)

### Manuell installation
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip i2c-tools python3-smbus
git clone https://github.com/IKKAMP/fotbollsplan-bevattning.git
cd fotbollsplan-bevattning
python3 -m venv .venv
source .venv/bin/activate
pip install -r api_requirements.txt
pip install -r display_requirements.txt  # För display-stöd
cp api_.env.example api_.env
# sätt API_KEY i api_.env
```

### Konfigurera SMTP (E-postmeddelanden)
För att aktivera e-postmeddelanden vid healthcheck-problem, använd det interaktiva installationsskriptet:
```bash
python3 install.py
```

Scriptet guidar dig genom:
- SMTP-server och port (t.ex. smtp.gmail.com:587)
- E-postadress och lösenord
- Two-factor authentication (2FA) inställningar
- Mottagare för notifieringar
- Testning av konfigurationen med ett test-mejl

Alternativt kan du manuellt redigera `api_.env` och ställa in:
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
- `SMTP_FROM`, `SMTP_TO` (kommaseparerade mottagare)

**OBS för Gmail-användare med 2FA:** Generera ett "App Password" på https://myaccount.google.com/apppasswords

### Konfigurera Tailscale (Fjärråtkomst)
Tailscale installeras automatiskt om du använder `setup.py`. För manuell installation:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```

Tailscale ger säker fjärråtkomst via SSH utan att öppna portar eller konfigurera portvidarebefordran. Efter installation:
- Kontrollera status: `sudo tailscale status`
- Hämta Tailscale IP: `sudo tailscale ip`

### Starta API manuellt
```bash
source .venv/bin/activate
uvicorn api_main:app --host 0.0.0.0 --port 8000
```
Test: `curl -H "X-API-Key: <nyckel>" http://localhost:8000/status`

### Starta Display Manager
```bash
source .venv/bin/activate
python3 display_manager.py --enable-scheduler
```
Se [DISPLAY_MANAGER.md](DISPLAY_MANAGER.md) för fullständig dokumentation.

### systemd (service)
Kopiera `systemd/bevattning-api.service` till `/etc/systemd/system/`, justera sökvägar/användare vid behov.
```bash
sudo systemctl daemon-reload
sudo systemctl enable bevattning-api
sudo systemctl start bevattning-api
```

## Modbus-register (PLC)
- **MW10** Remote_Command (50=start auto, PLC nollar ej).
- **MW20** Set_Tid_Center (min, 0..240, default 30 via ST-fallback vid 0).
- **MW21** Set_Tid_Horn (min, 0..240, default 15 via ST-fallback vid 0).
- **MW30** Markfukt % (skrivs av Python/extern ELLER skalas från analog input %IW0 i PLC).
  - **Dual-mode operation:** 
    - PLC kontinuerligt: Läser %IW0 (0-10V = 0-27648) och skalar till 0-100% varje scan-cykel
    - Python skrivning: Skriver direkt till MW30 (överskrider PLC-skalning till nästa PLC-cykel)
    - **OBS:** Sista skrivningen vinner - Python-skrivning är temporär, PLC skriver över vid nästa cykel om analog sensor är ansluten
  - **Rekommendation:** Använd antingen analog sensor ELLER Python-skrivning, inte båda samtidigt
  - Värdeområde: 0-100%
- **MW31** Regen_24h_mm (skrivs av Python/extern).
- **MW32** Temp_C (skrivs av Python/extern).
- **MW33** AutoOverride (1=forcera körning, hoppa fukt/regn-block).
- **MW34** RegenThreshold_mm (default 5 om 0).
- **MW35** MoistureThreshold (default 80 om 0).
- **MW40** OpenDelaySec (default 5 om 0) – ventiler öppnar, pump startar efter denna.
- **MW41** PauseDelaySec (default 10 om 0) – paus mellan zoner.
- **MW42** CloseDelaySec (default 10 om 0) – pump av, vänta, stäng ventiler.
- **MW50** Status_CurrentZone
- **MW51** Status_PumpOn (1/0)
- **MW52** Status_Steg
- **MW53** SelectedZoneReg (vald zon)
- **MW60** ModeRegister (1=Auto, 0=Manual override)
- **MW61** ManualStartReg (skriv 1 för manuell start, PLC nollar)
- **MW63** SetSelectedZoneReg (skriv 1..7, PLC nollar)
- **MW64** ManualRunTimeReg (DEPRECATED - manuellt läge använder nu auto-tider)
- **MW70** HeartbeatReg (bit0 togglar varje ~1s)
- **MW71** HeartbeatCountReg (0..65535, ++ varje ~1s)
- **MW72** EventMaskReg (bitmask)
  - bit0: E-stop aktiv
  - bit1: Fukt/regen-block
  - bit2: Sekvens aktiv
  - bit3: Anti-kollision aktiv (start blockerad när sekvens/pump aktiv)
  - bit4: AutoOverride aktiv
- **MW73** BlockReasonReg
  - 0=OK
  - 1=Regen > threshold
  - 2=Moisture > threshold
  - 3=Anti-kollision/pump upptagen
  - 4=E-stop
- **MW80** TestMode (1=testläge aktivt, 0=inaktivt)
- **MW81** TestZoneResult (bitmask för testade zoner 1-7)
- **MW82** ErrorReset (skriv 1 för att nollställa fel, PLC nollar)
  - Nollställer BlockReason (utom E-stop som måste åtgärdas fysiskt)
  - Återställer fastnade sekvenser
  - Rensar anti-kollision om ingen sekvens kör
- **MW100** ModeSwitch (Lokal/Fjärr-styrning)
  - 0=Neutral (ingen ändring, default)
  - 1=Lokalt läge (fysisk styrning aktiverad, fjärrkommandon blockerade)
  - 2=Fjärrläge (fjärrkommandon aktiverade)
  - Fysisk 1-0-2 switch skriver värde och återgår automatiskt till 0

## Sekvens & anti-vattenslag
- **Start (auto):** Ventil för zon öppnas, OpenDelay löper, därefter pump på och kör-timer. Auto-läge kör alla zoner 1-7.
- **Start (manual):** Välj zon med display-knappar (Button 1 ökar, Button 2 minskar, håll 3s för att bekräfta). Tryck fysisk Start-knapp. Manual-läge kör **endast den valda zonen**, med samma tider som auto-läge.
- **Zonbyte:** När körtid är slut: pump av först, CloseDelay, stäng ventiler, PauseDelay, nästa zon, OpenDelay, pump på.
- **Stop/E-stop:** Pump av direkt, CloseDelay, stäng ventiler. E-stop nollar sekvens och blockreason=4.
- **LED-indikatorer:** BORTTAGNA - aktiv zon och återstående tid visas på system-display istället.
- **Display-knappar:** Button 1 (öka zon), Button 2 (minska zon). Håll knapp i 3 sekunder för att bekräfta val.
- **21:00 auto-läge övergång:** Systemet övergår passivt till auto-läge kl 21:00 dagligen. Om en sekvens körs fortsätter den utan avbrott och övergången sker efteråt.

## Python Open-Meteo-controller
- Fil: `bevattning_controller.py`
- Hämtar väderdata från Open-Meteo (gratis, inget API-nyckel behövs)
- Typisk körning (en gång):
  ```bash
  python3 bevattning_controller.py --auto-start
  ```
- Loop:
  ```bash
  python3 bevattning_controller.py --loop --interval 60 --auto-start
  ```
- Flaggor: `--simulate`, `--dry-run`, `--read-markfukt`, `--rain-threshold`, `--moisture-threshold`, `--temp-min`.

## Python Scheduler (Auto-bevattning kl 01:00)
- Fil: `bevattning_scheduler.py`
- Kör daglig auto-bevattning kl 01:00 med villkorskontroller
- Kontrollerar BlockReason (MW73) innan start - blockerar om värde != 0
- Typisk körning (kontinuerlig schemaläggare):
  ```bash
  python3 bevattning_scheduler.py --auto-start
  ```
- Körning nu (för test):
  ```bash
  python3 bevattning_scheduler.py --run-now --auto-start
  ```
- Kör en gång vid nästa schemalagda tid:
  ```bash
  python3 bevattning_scheduler.py --once --auto-start
  ```
- Ändra schematid:
  ```bash
  python3 bevattning_scheduler.py --schedule-hour 2 --schedule-minute 30 --auto-start
  ```
- Flaggor: samma som `bevattning_controller.py` plus `--schedule-hour`, `--schedule-minute`, `--run-now`, `--once`.

## FastAPI
- Endpoints (alla kräver `X-API-Key`):
  - `GET /status`
  - `GET /` (Webb-UI för styrning och övervakning)
  - `POST /command/start-auto` (pulserar MW10=50->0)
  - `POST /command/manual` `{ "zone": 1..7 }` (skriver MW63 och pulsar MW61, kör full sekvens med auto-tider)
  - `POST /command/set-zone` `{ "zone": 1..7 }` (sätter MW63 utan att starta)
  - `POST /command/set-manual-time` **DEPRECATED** (behålls för bakåtkompatibilitet, gör ingenting)
  - `POST /command/stop` (sätter Remote_Command=0 och ModeOverride=0 för att stoppa auto)
  - `POST /config` (tider, trösklar, markfukt, regen, temp, mode_override)
  
### Meny-system endpoints (nya funktioner):
  - `POST /menu/test-bevattning` `{ "zone": 1..7, "duration_seconds": 60 }` (Testa enskild zon eller alla zoner)
    - Om `zone` utelämnas testas alla zoner 1-7 sekventiellt
    - Standardtestlängd är 60 sekunder per zon
    - Resultat loggas i MW81 (TestZoneResult bitmask)
  - `POST /menu/lagesval?mode=0|1` (Växla mellan Manual (0) och Auto (1) läge)
    - Blockeras om E-stop är aktiv
  - `GET /menu/felsökning` (Hämta detaljerad felstatus och diagnostik)
    - Returnerar block reason, eventmask, och tolkning av systemtillstånd
  - `POST /menu/reset-error` (Återställ pump-fel och zonlogik)
    - Pulserar MW82 (ErrorReset) för att nollställa PLC-fel

### Process View och Väderdata endpoints (Nya funktioner):
  - `GET /rain-forecast` (Hämta regnprognos från Open-Meteo)
    - Returnerar förväntad nederbörd nästa 24 timmar
    - Returnerar historisk nederbörd senaste 7 dagarna
    - Använder Open-Meteo API (gratis, inget API-nyckel behövs)
    - Konfigurerbara koordinater via `LATITUDE` och `LONGITUDE` miljövariabler
  - `GET /process-view` (Hämta live processtatus för grafisk visualisering)
    - Zonsstatus (aktiv/inaktiv) för alla zoner 1-7
    - Pumpstatus (på/av)
    - Sekvensstatus (aktivt steg, aktuell zon)
    - Felstatus (e-stop, markfukt-block, regn-block, anti-kollision)
    - Miljödata (markfukt, regn 24h, temperatur)
    - Konfiguration (tid_center, tid_horn)
    - Mode-status (lokalt/fjärr)
  - `POST /zone-control` `{ "zone": 1..7, "action": "start"|"stop" }` (Styr individuella zoner)
    - `action: "start"` - Starta vald zon (använder auto-tider)
    - `action: "stop"` - Stoppa all bevattning
    - Används av Dash Process View för grafisk zonkontroll

## Dash Process View (Grafisk Visualisering)
Ett grafiskt webb-gränssnitt byggt med Plotly Dash för realtidsövervakning och styrning.

### Funktioner
- **Zonöversikt:** Grafisk visualisering av alla 7 zoner med färgkodad status
  - Grön: Aktiv zon
  - Orange: Vald zon (men inte aktiv)
  - Grå: Inaktiv zon
- **Pumpstatus:** Live status av pump (på/av) med visuell indikator
- **Sekvensstatus:** Aktuellt steg och zon i pågående sekvens
- **Felvisualisering:** Grafiska varningar för systemfel
  - E-stop (röd varning)
  - Markfukt-block (orange)
  - Regn-block (orange)
  - Anti-kollision (orange)
- **Zonkontroll:** Klickbara kontroller för att starta/stoppa zoner
- **Regnprognos:** Graf över förväntad nederbörd nästa 24 timmar
- **Regnhistorik:** Graf över nederbörd senaste 7 dagarna
- **Miljödata:** Live visning av markfukt, regn 24h, temperatur
- **Auto-uppdatering:** Systemet uppdateras automatiskt var 5:e sekund

### Starta Dash Process View
```bash
source .venv/bin/activate
python3 dash_app.py
```

Dash-appen startar på `http://0.0.0.0:8050` (konfigurerbart via miljövariabler).

### Miljövariabler för Dash
- `API_URL` - URL till FastAPI backend (default: `http://127.0.0.1:8000`)
- `API_KEY` - API-nyckel för autentisering
- `DASH_PORT` - Port för Dash-appen (default: `8050`)
- `DASH_HOST` - Host för Dash-appen (default: `0.0.0.0`)
- `LATITUDE` - Latitud för väderdata (default: `55.6050` - Malmö)
- `LONGITUDE` - Longitud för väderdata (default: `13.0038` - Malmö)

### Systemd service för Dash (valfritt)
För att köra Dash Process View som en systemd-tjänst, skapa en service-fil:

```ini
[Unit]
Description=Bevattning Dash Process View
After=network.target bevattning-api.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/fotbollsplan-bevattning
Environment="PATH=/home/pi/fotbollsplan-bevattning/.venv/bin"
EnvironmentFile=/home/pi/fotbollsplan-bevattning/api_.env
ExecStart=/home/pi/fotbollsplan-bevattning/.venv/bin/python3 /home/pi/fotbollsplan-bevattning/dash_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Installera och starta:
```bash
sudo cp systemd_dash-process-view.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dash-process-view
sudo systemctl start dash-process-view
```

## Healthcheck
- Script: `python healthcheck.py`
- Env: `API_URL` (default `http://127.0.0.1:8000/status`), `API_KEY`, `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_TO` (komma-separerad).

## Säkerhet
- API-nyckel krävs för alla anrop (`X-API-Key`).
- Kör på lokalt nät; exponera externt endast via VPN eller reverse proxy med TLS.
- Rate-limit på reverse proxy om utsatt.
- Pythonlager är icke-realtid; säkerhetskritiska delar ligger i PLC/ST.

## I/O-mappning (UNIPI 1.1, förslag)
- Ventil_1..7: `%QX0.0`..`%QX0.6`
- Pump_enable (till LOGO/VFD): `%QX0.7`
- LED_1..7: **BORTTAGNA** (aktiv zon visas på display istället)
- Analog In:
  - Markfuktgivare: `%IW0` (0-10V analog input, skalas till 0-100% i PLC)
- Ingångar: 
  - Stop `%IX0.0`
  - Start `%IX0.1`
  - Auto/Man `%IX0.2`
  - Next `%IX0.3` (deprecated)
  - Display_Button_1 `%IX0.4` (öka zon)
  - Test `%IX0.5`
  - Blow `%IX0.6`
  - E-Stop NC `%IX0.7`
  - Display_Button_2 `%IX1.0` (minska zon)

## Snabbtest av API
```bash
# Hämta status
curl -H "X-API-Key: <din-nyckel>" http://localhost:8000/status

# Starta auto-program (alla zoner enligt schema)
curl -X POST -H "X-API-Key: <din-nyckel>" http://localhost:8000/command/start-auto

# Starta natt-program (samma som auto, kör alla zoner)
curl -X POST -H "X-API-Key: <din-nyckel>" http://localhost:8000/command/start-night-program

# Starta manuell körning - zon 2, 5 minuter (default)
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <din-nyckel>" \
  -d '{"zone":2}' http://localhost:8000/command/manual

# Starta manuell körning - zon 2, 10 minuter
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <din-nyckel>" \
  -d '{"zone":2}' http://localhost:8000/command/manual

# Testa alla zoner (försäsongskontroll) - 60 sekunder per zon
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <din-nyckel>" \
  -d '{"duration_seconds":60}' http://localhost:8000/menu/test-bevattning

# Testa enskild zon (zon 3) - 60 sekunder
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <din-nyckel>" \
  -d '{"zone":3,"duration_seconds":60}' http://localhost:8000/menu/test-bevattning

# Växla till Auto-läge
curl -X POST -H "X-API-Key: <din-nyckel>" \
  http://localhost:8000/menu/lagesval?mode=1

# Växla till Manuellt läge
curl -X POST -H "X-API-Key: <din-nyckel>" \
  http://localhost:8000/menu/lagesval?mode=0

# Ställ in Lokal/Fjärr-styrning - Lokalt läge
curl -X POST -H "X-API-Key: <din-nyckel>" \
  http://localhost:8000/set-mode/1

# Ställ in Lokal/Fjärr-styrning - Fjärrläge
curl -X POST -H "X-API-Key: <din-nyckel>" \
  http://localhost:8000/set-mode/2

# Ställ in Lokal/Fjärr-styrning - Neutral (ingen ändring)
curl -X POST -H "X-API-Key: <din-nyckel>" \
  http://localhost:8000/set-mode/0

# Hämta felsökningsinformation
curl -H "X-API-Key: <din-nyckel>" http://localhost:8000/menu/felsökning

# Återställ pump-fel och zonlogik
curl -X POST -H "X-API-Key: <din-nyckel>" \
  http://localhost:8000/menu/reset-error

# === PROCESS VIEW & VÄDERDATA ENDPOINTS ===

# Hämta regnprognos (nästa 24h + senaste 7 dagarna)
curl -H "X-API-Key: <din-nyckel>" http://localhost:8000/rain-forecast

# Hämta live processtatus (zoner, pump, fel, miljödata)
curl -H "X-API-Key: <din-nyckel>" http://localhost:8000/process-view

# Starta zon via zone-control
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <din-nyckel>" \
  -d '{"zone":5,"action":"start"}' http://localhost:8000/zone-control

# Stoppa bevattning via zone-control
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <din-nyckel>" \
  -d '{"zone":1,"action":"stop"}' http://localhost:8000/zone-control
```

## Rekommenderad drift
- PLC kör ST-programmet (task 100 ms).
- Python SMHI-controller körs t.ex. via cron eller systemd timer för periodiska uppdateringar av väder/markfukt.
- **Auto-bevattning:** Använd `bevattning_scheduler.py` med systemd timer för daglig körning kl 01:00.
- FastAPI kör som systemd-tjänst för app/webb-styrning.
- Display Manager körs som systemd-tjänst för lokal styrning och övervakning.
- Se till att Siemens LOGO/VFD hanterar mjukstart; pumpstyrningen sker via `Signal_Pump` (på/av), men rampning sköts av VFD.

### Automatisk bevattning (01:00 dagligen)

#### Alternativ 1: Systemd timer (rekommenderat)
Installera systemd timer för daglig auto-bevattning:
```bash
sudo cp systemd_bevattning-scheduler.timer /etc/systemd/system/
sudo cp systemd_bevattning-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bevattning-scheduler.timer
sudo systemctl start bevattning-scheduler.timer
```

Verifiera timer-status:
```bash
sudo systemctl status bevattning-scheduler.timer
sudo systemctl list-timers bevattning-scheduler.timer
```

#### Alternativ 2: Cron
Alternativt kan du använda cron. Se `crontab.example` för konfiguration:
```bash
crontab -e
# Lägg till följande rad:
0 1 * * * /home/pi/fotbollsplan-bevattning/.venv/bin/python3 /home/pi/fotbollsplan-bevattning/bevattning_scheduler.py --run-now --auto-start >> /home/pi/bevattning_scheduler.log 2>&1
```

Scheduler kontrollerar automatiskt block-villkor (MW73 BlockReason) innan auto-bevattning startar:
- BlockReason=0: OK, bevattning körs
- BlockReason=1: Regn över tröskel, bevattning blockerad
- BlockReason=2: Markfukt över tröskel, bevattning blockerad  
- BlockReason=3: Anti-kollision/pump upptagen, bevattning blockerad
- BlockReason=4: E-stop aktiv, bevattning blockerad

## Viktigt
- Vattenslag: ventiler öppnas före pumpstart; pump stängs av före ventilstängning och vid zonbyten används CloseDelay + PauseDelay.
- Endast auktoriserade användare: håll API-nyckel hemlig; exponera inte öppet utan TLS/VPN.
