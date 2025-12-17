# Fotbollsplan bevattning

## Arkitektur
- **PLC (ST):** Säker/sekvenslogik, anti-vattenslag, E-stop, zonbyte.
- **Python controller:** Hämtar Open-Meteo, markfukt (valfritt), skriver Modbus-register, pulserar start.
- **FastAPI-backend:** API/Webb-UI + Modbus-brygga. Skyddas med API-nyckel.
- **Display Manager:** Hanterar två I2C LCD-displayer för status och manuell styrning.
- **Hårdvara:** UNIPI 1.1, Raspberry Pi 3 (Debian Bookworm). Pump_enable styr Siemens LOGO → VFD (mjukstart).

## Bygg & kör på Raspberry Pi
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
- **MW30** Markfukt % (skrivs av Python/extern).
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
- **MW64** ManualRunTimeReg (min, 1..240, default 5)
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

## Sekvens & anti-vattenslag
- **Start (auto/manual):** Ventil för zon öppnas, OpenDelay löper, därefter pump på och kör-timer.
- **Zonbyte:** När körtid är slut: pump av först, CloseDelay, stäng ventiler, PauseDelay, nästa zon, OpenDelay, pump på.
- **Stop/E-stop:** Pump av direkt, CloseDelay, stäng ventiler. E-stop nollar sekvens och blockreason=4.
- **Next-knapp:** Roterar SelectedZone 1→7→1. Vid omstart initieras SelectedZone=1.
- **Manuell start:** Välj zon (rotationsknapp/display), ställ tid, och bekräfta med fysiska startknappen.

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
  - `POST /command/start-auto` (pulserar MW10=50->0)
  - `POST /command/manual` `{ "zone": 1..7, "minutes": <valfritt> }` (skriver MW64 om minutes anges, skriver MW63 och pulsar MW61)
  - `POST /command/set-zone` `{ "zone": 1..7 }` (sätter MW63 utan att starta)
  - `POST /command/set-manual-time` `{ "minutes": 1..240 }` (sätter MW64 utan att starta)
  - `POST /command/stop` (sätter Remote_Command=0 och ModeOverride=0 för att stoppa auto)
  - `POST /config` (tider, trösklar, markfukt, regen, temp, manual_time, mode_override)

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
- LED_1..7: `%QX1.0`..`%QX1.6`
- Ingångar: Stop `%IX0.0`, Start `%IX0.1`, Auto/Man `%IX0.2`, Next `%IX0.3`, Test `%IX0.5`, Blow `%IX0.6`, E-Stop NC `%IX0.7`

## Snabbtest av API
```bash
curl -H "X-API-Key: <din-nyckel>" http://localhost:8000/status
curl -X POST -H "X-API-Key: <din-nyckel>" http://localhost:8000/command/start-auto
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <din-nyckel>" \
  -d '{"zone":2,"minutes":5}' http://localhost:8000/command/manual
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
