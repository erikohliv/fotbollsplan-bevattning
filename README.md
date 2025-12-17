# Fotbollsplan bevattning

## Arkitektur
- **PLC (ST):** Säker/sekvenslogik, anti-vattenslag, E-stop, zonbyte.
- **Python controller:** Hämtar SMHI, markfukt (valfritt), skriver Modbus-register, pulserar start.
- **FastAPI-backend:** API/Webb-UI + Modbus-brygga. Skyddas med API-nyckel.
- **Hårdvara:** UNIPI 1.1, Raspberry Pi 3 (Debian Bookworm). Pump_enable styr Siemens LOGO → VFD (mjukstart).

## Bygg & kör på Raspberry Pi
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
git clone https://github.com/IKKAMP/fotbollsplan-bevattning.git
cd fotbollsplan-bevattning
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
cp api/.env.example api/.env
# sätt API_KEY i api/.env
```

### Starta API manuellt
```bash
cd api
source ../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```
Test: `curl -H "X-API-Key: <nyckel>" http://localhost:8000/status`

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
- **Manuell start via display/LED:** I manuellt läge startas vald zon automatiskt när den väljs (LED visar vald/aktiv zon), ingen separat startknapp behövs.

## Python SMHI-controller
- Fil: `bevattning_controller.py`
- Typisk körning (en gång):
  ```bash
  python3 bevattning_controller.py --auto-start
  ```
- Loop:
  ```bash
  python3 bevattning_controller.py --loop --interval 60 --auto-start
  ```
- Flaggor: `--simulate`, `--dry-run`, `--read-markfukt`, `--rain-threshold`, `--moisture-threshold`, `--temp-min`.

## FastAPI
- Endpoints (alla kräver `X-API-Key`):
  - `GET /status`
  - `POST /command/start-auto` (pulserar MW10=50->0)
  - `POST /command/manual` `{ "zone": 1..7, "minutes": <valfritt> }` (skriver MW64 om minutes anges, skriver MW63 och pulsar MW61)
  - `POST /command/stop` (sätter Remote_Command=0 och ModeOverride=0 för att stoppa auto)
  - `POST /config` (tider, trösklar, markfukt, regen, temp, manual_time, mode_override)

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
- FastAPI kör som systemd-tjänst för app/webb-styrning.
- Se till att Siemens LOGO/VFD hanterar mjukstart; pumpstyrningen sker via `Signal_Pump` (på/av), men rampning sköts av VFD.

## Viktigt
- Vattenslag: ventiler öppnas före pumpstart; pump stängs av före ventilstängning och vid zonbyten används CloseDelay + PauseDelay.
- Endast auktoriserade användare: håll API-nyckel hemlig; exponera inte öppet utan TLS/VPN.
