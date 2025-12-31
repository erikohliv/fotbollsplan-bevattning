# Fotbollsplan bevattning

## Arkitektur
- **PLC (ST):** Säker/sekvenslogik, anti-vattenslag, E-stop, zonbyte, flödesvaktsskydd.
- **Python controller:** Hämtar Open-Meteo, markfukt (valfritt), skriver Modbus-register, pulserar start.
- **FastAPI-backend:** API/Webb-UI + Modbus-brygga. Skyddas med API-nyckel.
- **Display Manager:** Hanterar två I2C LCD-displayer för status och manuell styrning. Menyknappar läses från PLC via Modbus.
- **Hårdvara:** UNIPI 1.1, Raspberry Pi 3 (Debian Bookworm). Pump styrs direkt via Relä 8 → Mjukstartare. Tryckvakt (DI5) och Flödesvakt (DI7) via Terminal X3 för säkerhetsövervakning.

## Rörledningsnät och Zonspecifikationer
Systemet använder ett hybridnät med PEM 90/75/50 rör. **Viktigt**: Zon 7 har PEM 50 (mindre dimension) medan Zon 5 har PEM 75, vilket ger naturlig tryckdämpning i Zon 7. Se [PIPE_NETWORK_DOCUMENTATION.md](PIPE_NETWORK_DOCUMENTATION.md) för detaljerad förklaring av hydraulik, tryckskillnader och varför dimensionen spelar roll.

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
Kopiera `systemd_bevattning-api.service` till `/etc/systemd/system/bevattning-api.service`, justera sökvägar/användare vid behov.
```bash
sudo cp systemd_bevattning-api.service /etc/systemd/system/bevattning-api.service
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
- **MW33** Pressure_Switch_Status (digital: 0=ingen tryck, 1=tryck OK - från DI5 via Terminal X3).
  - **ÄNDRING från analog till digital**: Tidigare analog 0-100%, nu digital switch
  - Tryckvakt ansluten till %IX0.4 (DI5)
  - Polaritet konfigurerbar i PLC via PRESSURE_OK_STATE (TRUE=NO, FALSE=NC)
  - Se MW54 för larmstatus
- **MW34** AutoOverride (1=forcera körning, hoppa fukt/regn-block).
- **MW35** RegenThreshold_mm (default 5 om 0).
- **MW36** MoistureThreshold (default 80 om 0).
- **MW40** OpenDelaySec (default 5 om 0) – ventiler öppnar, pump startar efter denna.
- **MW41** PauseDelaySec (default 10 om 0) – paus mellan zoner.
- **MW42** CloseDelaySec (default 10 om 0) – pump av, vänta, stäng ventiler.
- **MW50** Status_CurrentZone
- **MW51** Status_PumpOn (1/0)
- **MW52** Status_Steg
- **MW53** SelectedZoneReg (vald zon)
- **MW54** PressureAlarmReg (tryckvakt larm)
  - 0=OK
  - 1=Timeout (inget tryck inom 10s efter pumpstart)
  - 2=Oväntat tryck (tryck detekterat när pump är av)
- **MW55** FlowSwitchStatus (digital: 0=ingen flöde, 1=flöde OK - från DI7 via Terminal X3)
  - Flödesvakt ansluten till %IX0.6 (DI7)
  - Polaritet konfigurerbar i PLC via FLOW_OK_STATE (TRUE=NO, FALSE=NC)
  - Se MW56 för larmstatus
- **MW56** FlowAlarmReg (flödesvakt larm)
  - 0=OK
  - 1=Initial timeout
  - 2=Torrkörning (flöde förlorat under drift, >3s utan flöde)
- **MW60** ModeRegister (1=Auto, 0=Manual override)
- **MW61** ManualStartReg (skriv 1 för manuell start, PLC nollar)
- **MW63** SetSelectedZoneReg (skriv 1..7, PLC nollar)
- **MW64** MenuButtonsReg (bitmask för menyknappar från DI11-DI14)
  - bit0: Vänster (DI11)
  - bit1: Höger (DI12)
  - bit2: OK (DI13)
  - bit3: Tillbaka (DI14)
- **MW65** ManualRunTimeReg (manuell körtid i minuter, 1-240)
  - Används när manual mode triggas via display
  - Om ej satt, använder system Set_Tid_Center/Horn
- **MW66** SpecialModeReg (trigger för special modes)
  - 0=ingen åtgärd
  - 1=Test mode (kort testkörning)
  - 2=Blow mode (bläs ut/vinterberedning)
  - PLC nollar registret efter start
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
  - 5=Tryckfel (inget tryck efter pumpstart)
  - 6=Flödesfel (torrkörning, inget flöde under drift)
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
  - Fysisk 1-0-2 switch har två separata ingångar: DI3 (Auto) och DI10 (Manual)

## Sekvens & anti-vattenslag
- **Start (auto):** Ventil för zon öppnas, OpenDelay löper, därefter pump på och kör-timer. Auto-läge kör alla zoner 1-7 med Set_Tid_Center/Horn.
- **Start (manual):** Använd displaymenyn: MODE→Manual, välj zon och tid (MW65), bekräfta. Kör **endast den valda zonen** med vald tid.
- **Start (test):** Använd displaymenyn: MODE→Test, välj zon, bekräfta. Kort testkörning på vald zon via MW66=1.
- **Start (blow):** Använd displaymenyn: MODE→Blow, välj zon, bekräfta. Blow-out mode på vald zon via MW66=2.
- **Zonbyte:** När körtid är slut: pump av först, CloseDelay, stäng ventiler, PauseDelay, nästa zon, OpenDelay, pump på.
- **Stop/E-stop:** Pump av direkt, CloseDelay, stäng ventiler. E-stop nollar sekvens och blockreason=4.
- **Säkerhetsövervakning:**
  - **Tryckvakt (DI5):** Digital ingång. Vid pumpstart måste tryck detekteras inom 10s, annars alarm (MW54=1) och pump stoppas (BlockReason=5).
  - **Flödesvakt (DI7):** Digital ingång. Om flöde försvinner under drift i mer än 3s, alarm (MW56=2) och pump stoppas (BlockReason=6).
  - **Polaritet:** Båda givare kan konfigureras för NO (Normally Open) eller NC (Normally Closed) via PLC-konstanter PRESSURE_OK_STATE och FLOW_OK_STATE.
  - **Reset:** Använd MW82 (ErrorReset) för att nollställa alarm och återställa systemet.
- **Displaymeny:** Komplett meny via knappar DI11-DI14: OVERVIEW → MODE → ZONE → TIME (manual) → CONFIRM (håll OK >2s).
- **LED-indikatorer:** BORTTAGNA - aktiv zon och återstående tid visas på system-display istället.
- **Display-knappar:** Button 1 (öka zon), Button 2 (minska zon). Håll knapp i 3 sekunder för att bekräfta val.
- **21:00 auto-läge övergång:** Systemet övergår passivt till auto-läge kl 21:00 dagligen. Om en sekvens körs fortsätter den utan avbrott och övergången sker efteråt.

## Konfigurering av givare (Tryckvakt och Flödesvakt)
Tryckvakten och flödesvakten är digitala givare som kan vara antingen NO (Normally Open) eller NC (Normally Closed). 

**Ändra givarpolaritet i PLC-koden:**
I filen `Fotbollsplan_Master_Version12.st`, hitta följande konstanter i VAR-sektionen:
```structured-text
(* Safety monitoring: Configurable sensor polarity *)
PRESSURE_OK_STATE : BOOL := TRUE;   (* TRUE=NO (Normally Open), FALSE=NC (Normally Closed) *)
FLOW_OK_STATE : BOOL := TRUE;       (* TRUE=NO (Normally Open), FALSE=NC (Normally Closed) *)
```

**Exempel:**
- Om tryckvakten är kopplad NC (Normally Closed) - öppnar när tryck finns:
  ```structured-text
  PRESSURE_OK_STATE : BOOL := FALSE;
  ```
- Om flödesvakten är kopplad NO (Normally Open) - sluter när flöde finns:
  ```structured-text
  FLOW_OK_STATE : BOOL := TRUE;
  ```

**Verifiering:**
1. Se till att pumpen är avstängd
2. Läs MW33 (Pressure_Switch_Status) - ska vara 0 när inget tryck
3. Läs MW55 (FlowSwitchStatus) - ska vara 0 när inget flöde
4. Om värdena är felaktiga, invertera motsvarande konstant i PLC-koden

**Timeout-inställningar:**
PLC-konstanter för timeout-övervakning kan justeras vid behov:
```structured-text
PRESSURE_TIMEOUT_SEC : INT := 10;   (* Sekunder att vänta på tryck efter pumpstart *)
FLOW_TIMEOUT_SEC : INT := 3;        (* Sekunder utan flöde under drift innan larm *)
```

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

## Automatic System Updates

Systemet stöder automatisk deployment av kod-uppdateringar till Raspberry Pi via GitHub Actions. När ändringar pushas till `main`-branchen, deployas de automatiskt till produktionssystemet.

### Hur det fungerar

**GitHub Actions Workflow:**
När kod pushas till `main`-branchen:
1. GitHub Actions ansluter till Raspberry Pi via SSH
2. Senaste koden hämtas från repository
3. Python-beroenden uppdateras
4. Systemtjänster startas om automatiskt

**Deployment-processen:**
- `bevattning-api` tjänsten startas om (REST API och Webb-UI)
- `display-manager` tjänsten startas om (om den körs)
- `bevattning-scheduler` tjänsten startas om (om den körs)

### Förutsättningar för automatisk deployment

#### 1. SSH-åtkomst till Raspberry Pi

Generera ett SSH-nyckelpar för GitHub Actions (kör på din utvecklingsmaskin):
```bash
ssh-keygen -t ed25519 -f ~/.ssh/rpi_deploy_key -C "github-actions-deploy"
```

Kopiera den publika nyckeln till Raspberry Pi:
```bash
ssh-copy-id -i ~/.ssh/rpi_deploy_key.pub pi@<raspberry-pi-ip>
```

Testa SSH-anslutningen:
```bash
ssh -i ~/.ssh/rpi_deploy_key pi@<raspberry-pi-ip>
```

#### 2. Konfigurera GitHub Secrets

Navigera till ditt GitHub repository → Settings → Secrets and variables → Actions

Skapa följande secrets:

| Secret Name | Beskrivning | Exempel |
|-------------|-------------|---------|
| `RPI_HOST` | IP-adress eller värdnamn för Raspberry Pi | `192.168.1.100` eller `bevattning.local` |
| `RPI_USER` | Användarnamn på Raspberry Pi | `pi` |
| `RPI_SSH_KEY` | Privat SSH-nyckel (hela innehållet i `~/.ssh/rpi_deploy_key`) | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` |

**Viktigt:** För `RPI_SSH_KEY`, kopiera hela innehållet i den privata nyckelfilen, inklusive headers:
```bash
cat ~/.ssh/rpi_deploy_key
```

#### 3. Tillåt sudo utan lösenord för systemctl-kommandon

På Raspberry Pi, skapa en sudoers-fil för att tillåta `pi`-användaren att starta om tjänster utan lösenord:

```bash
sudo visudo -f /etc/sudoers.d/bevattning-deploy
```

Lägg till följande rader:
```
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart bevattning-api
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart display-manager
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart bevattning-scheduler
pi ALL=(ALL) NOPASSWD: /bin/systemctl is-active bevattning-api
pi ALL=(ALL) NOPASSWD: /bin/systemctl is-active display-manager
pi ALL=(ALL) NOPASSWD: /bin/systemctl is-active bevattning-scheduler
```

Spara och stäng filen (`:wq` i vi/vim).

### Manuell deployment

Om du behöver köra deployment manuellt på Raspberry Pi:

```bash
cd /home/pi/fotbollsplan-bevattning
./scripts/deploy.sh
```

Deployment-scriptet utför:
1. Hämtar senaste koden från git
2. Aktiverar Python virtual environment
3. Installerar/uppdaterar dependencies
4. Startar om alla systemtjänster
5. Verifierar att tjänsterna körs

### Alternativ: Git Post-Receive Hook

Om du föredrar att köra deployment direkt från Raspberry Pi (utan GitHub Actions), kan du använda en Git post-receive hook:

**Installation:**
```bash
cd /home/pi/fotbollsplan-bevattning
cp scripts/post-receive.sample .git/hooks/post-receive
chmod +x .git/hooks/post-receive
```

**Användning:**
Deployment sker automatiskt när du pushar till `main`-branchen från Raspberry Pi:
```bash
git push origin main
```

**OBS:** Git hook-metoden kräver att repository är konfigurerat som en git remote på Raspberry Pi.

### Felsökning av deployment

**Kontrollera GitHub Actions-loggar:**
1. Gå till ditt repository på GitHub
2. Klicka på "Actions"-fliken
3. Välj den senaste workflow-körningen
4. Granska loggarna för eventuella fel

**Kontrollera tjänststatus på Raspberry Pi:**
```bash
# Kontrollera alla tjänster
systemctl status bevattning-api
systemctl status display-manager
systemctl status bevattning-scheduler

# Se loggar för en specifik tjänst
journalctl -u bevattning-api -n 50
```

**Vanliga problem:**

| Problem | Lösning |
|---------|---------|
| SSH-anslutning misslyckas | Kontrollera att `RPI_HOST` är korrekt och att Raspberry Pi är tillgänglig |
| Permission denied | Kontrollera att SSH-nyckeln är korrekt konfigurerad och att sudoers-filen är rätt |
| Service restart failed | Kontrollera att tjänsterna är installerade med `systemctl list-unit-files` |
| Git pull fails | Kontrollera att git repository är korrekt konfigurerat på Raspberry Pi |

### Säkerhetsöverväganden

- **SSH-nycklar:** Håll privata SSH-nycklar hemliga. Lägg aldrig till dem i repository.
- **GitHub Secrets:** Secrets är krypterade och exponeras aldrig i loggar.
- **Sudo-begränsningar:** sudoers-konfigurationen tillåter endast specifika systemctl-kommandon, inte full root-åtkomst.
- **Nätverkssäkerhet:** Använd VPN (t.ex. Tailscale) om Raspberry Pi är åtkomlig över internet.

## Säkerhet
- API-nyckel krävs för alla anrop (`X-API-Key`).
- Kör på lokalt nät; exponera externt endast via VPN eller reverse proxy med TLS.
- Rate-limit på reverse proxy om utsatt.
- Pythonlager är icke-realtid; säkerhetskritiska delar ligger i PLC/ST.

## I/O-mappning (UNIPI 1.1, uppdaterad hårdvara)
- Ventil_1..7: `%QX0.0`..`%QX0.6`
- Pump_enable (till Mjukstartare via Relä 8): `%QX0.7`
- LED_1..7: **BORTTAGNA** (aktiv zon visas på display istället)
- Analog In:
  - Markfuktgivare: `%IW0` (0-10V analog input, skalas till 0-100% i PLC)
- Digitala Ingångar: 
  - Stop `%IX0.0` (DI1 - Button_Stop)
  - Start `%IX0.1` (DI2 - Button_Start)
  - Auto-läge `%IX0.2` (DI3 - Switch_Auto från 1-0-2 brytare)
  - Reset `%IX0.3` (DI4 - Button_Reset)
  - Tryckvakt `%IX0.4` (DI5 - Switch_Pressure, NO/NC konfigurerbar)
  - Test `%IX0.5` (DI6 - Button_Test)
  - Flödesvakt `%IX0.6` (DI7 - Flow_Switch, NO/NC konfigurerbar)
  - Nödstopp `%IX0.7` (DI8 - E_Stop, NC)
  - Manual-läge `%IX1.1` (DI10 - Switch_Manual från 1-0-2 brytare)
  - E-Stop NC `%IX0.7` (DI8)
  - Manual-läge `%IX1.1` (DI10 - från 1-0-2 brytare)
  - Meny Vänster `%IX1.2` (DI11 - PLC-knapp)
  - Meny Höger `%IX1.3` (DI12 - PLC-knapp)
  - Meny OK `%IX1.4` (DI13 - PLC-knapp)
  - Meny Tillbaka `%IX1.5` (DI14 - PLC-knapp)

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
- Mjukstartare hanterar motorstart/stopp; pumpstyrningen sker via `Signal_Pump` (på/av, Relä 8), rampning sköts av mjukstartaren.

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
