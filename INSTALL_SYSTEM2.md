# 🚀 System 2.0 Installations-guide

Komplett guide för installation av **Fotbollsplan Bevattning System 2.0** på Raspberry Pi 4 med Debian Bookworm.

---

## 📋 Förutsättningar

### Hårdvara
- ✅ Raspberry Pi 4 (2GB+ RAM rekommenderat)
- ✅ microSD-kort (16GB+ rekommenderat)
- ✅ Nätverksanslutning (WiFi eller Ethernet)
- ✅ UniPi PLC med Modbus TCP-stöd
- ✅ (Valfritt) I2C LCD-display (20x4, adress 0x27 - Display 1)
- ✅ (Valfritt) I2C Arkadknappar via PCF8574 (adress 0x20)

### Programvara
- ✅ Raspberry Pi OS Lite (Bookworm, 64-bit rekommenderat)
- ✅ SSH aktiverat (för fjärråtkomst)
- ✅ Git installerat
- ✅ Python 3.11+ (ingår i Raspberry Pi OS Bookworm)

---

## 🎯 Snabbstart: Automatisk installation (10 minuter)

### Metod 1: Från GitHub (REKOMMENDERAT)

**Ett-kommando installation:**
```bash
curl -fsSL https://raw.githubusercontent.com/erikohliv/fotbollsplan-bevattning/main/setup.sh | sudo bash
```

Detta kommando:
1. Laddar ner installationsskriptet
2. Kör det med root-rättigheter
3. Installerar alla komponenter automatiskt

### Metod 2: Klona repository först

Om du vill granska koden före installation:
```bash
# 1. Klona repository
git clone https://github.com/erikohliv/fotbollsplan-bevattning.git
cd fotbollsplan-bevattning

# 2. Kör installation
sudo bash setup.sh
```

---

## 📦 Vad installeras?

Installationsskriptet utför följande:

### 1. ✅ Systempaket
- Python 3 och utvecklingsverktyg
- I2C-verktyg (i2c-tools, python3-smbus)
- Build-verktyg (build-essential, git, curl)
- Nätverksverktyg

### 2. ✅ I2C-aktivering
- Aktiverar I2C-gränssnittet för:
  - **Display 1** (LCD 20x4, adress 0x27)
  - **Arkadknappar** (PCF8574, adress 0x20)
- Lägger till användaren i i2c-gruppen
- Konfigurerar kernel-moduler

**OBS:** Omstart krävs för att I2C ska aktiveras helt!

### 3. ✅ Python Virtual Environment
- Skapar isolerad Python-miljö (`.venv`)
- **PEP 668-kompatibel** (fungerar på Debian Bookworm)
- Installerar alla beroenden från:
  - `api_requirements.txt` (FastAPI, pymodbus, etc.)
  - `display_requirements.txt` (smbus2 för I2C)

### 4. ✅ Miljövariabel-konfiguration
Interaktiv konfiguration av `api_.env`:

#### API och Modbus:
- **API_KEY**: API-nyckel för REST API-åtkomst
- **MODBUS_HOST**: PLC IP-adress (t.ex. 192.168.1.100)
- **MODBUS_PORT**: Modbus TCP-port (standard: 502)
- **MODBUS_UNIT**: Modbus Unit ID (standard: 1)

#### Väderdata (Håkanryd, Bromölla):
- **LATITUDE**: Latitud (standard: 56.05)
- **LONGITUDE**: Longitud (standard: 14.40)

#### SMTP E-post (valfritt):
För e-postnotifieringar vid fel:
- **SMTP_HOST**: SMTP-server (t.ex. smtp.gmail.com)
- **SMTP_PORT**: SMTP-port (standard: 587)
- **SMTP_USER**: E-postadress
- **SMTP_PASS**: E-postlösenord
- **SMTP_TO**: Mottagare (kommaseparerad lista)

**Gmail-användare med 2FA:** Generera ett "App Password" på https://myaccount.google.com/apppasswords

### 5. ✅ Superadmin-användare
- Skapar superadmin-konto för Webb-UI
- Lösenord hashas med bcrypt (säkert)
- Sparas i `superadmin.txt` (rättigheter: 600)

### 6. ✅ Tailscale (valfritt)
- Installerar Tailscale för säker fjärråtkomst
- Konfigurerar SSH över Tailscale
- **Ingen portvidarebefordran behövs!**

### 7. ✅ Systemd Services
Installerar och aktiverar följande tjänster:

| Tjänst | Beskrivning | Startläge |
|--------|-------------|-----------|
| `bevattning-api.service` | REST API & Webb-UI (FastAPI) | Automatisk start vid boot |
| `display-manager.service` | LCD-display hantering | Automatisk start vid boot |
| `bevattning-controller.service` | Väder-controller (Open-Meteo) | Automatisk start vid boot |
| `bevattning-scheduler.timer` | Auto-bevattning kl 01:00 | Automatisk start vid boot |

**Alla tjänster använder Python virtual environment** (`.venv`), vilket säkerställer PEP 668-kompatibilitet!

---

## 🔧 Efter installationen

### Steg 1: Starta om systemet

I2C-aktivering kräver omstart:
```bash
sudo reboot
```

### Steg 2: Verifiera I2C-enheter

Efter omstart, kontrollera att I2C-enheterna detekteras:
```bash
i2cdetect -y 1
```

**Förväntad output:**
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: 20 -- -- -- -- -- -- 27 -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
```

- `20` = Arkadknappar (PCF8574)
- `27` = Display 1 (LCD 20x4)

**Om enheterna inte syns:**
- Kontrollera kabeldragning
- Kontrollera att I2C är aktiverat: `lsmod | grep i2c`
- Kör: `sudo modprobe i2c-dev`

### Steg 3: Starta tjänsterna

Efter omstart, starta systemets tjänster:
```bash
# Starta alla tjänster
sudo systemctl start bevattning-api
sudo systemctl start display-manager
sudo systemctl start bevattning-controller

# Aktivera timer för auto-bevattning
sudo systemctl enable bevattning-scheduler.timer
sudo systemctl start bevattning-scheduler.timer
```

### Steg 4: Verifiera installation

Kontrollera att tjänsterna körs:
```bash
# Status för alla tjänster
systemctl status bevattning-api
systemctl status display-manager
systemctl status bevattning-controller

# Status för timer
systemctl list-timers bevattning-scheduler.timer
```

**Förväntad output för timer:**
```
NEXT                         LEFT       LAST PASSED UNIT                        ACTIVATES
Wed 2026-01-02 01:00:00 CET  5h 8min left -    -    bevattning-scheduler.timer  bevattning-scheduler.service
```

### Steg 5: Åtkomst till systemet

#### Webb-UI
Hitta din Raspberry Pi IP-adress:
```bash
hostname -I | awk '{print $1}'
```

Öppna webbläsare och gå till:
```
http://<raspberry-pi-ip>:8000
```

**API-dokumentation (Swagger):**
```
http://<raspberry-pi-ip>:8000/docs
```

#### Dash Process View
Grafisk visualisering av systemet (om installerat):
```
http://<raspberry-pi-ip>:8050
```

---

## 🧪 Hårdvarutester

Efter installation, testa hårdvaran för att säkerställa korrekt funktion:

### 1. Relay Test (PLC-anslutning)

Testar alla reläer och ingångar:
```bash
cd /home/pi/fotbollsplan-bevattning
source .venv/bin/activate
python3 relay_test.py --host <plc-ip>
```

**Vad som testas:**
- ✅ Relä 1-7 (ventiler)
- ✅ Relä 8 (pump) - endast om motorskydd (DI10) är AV
- ✅ Digitala ingångar (knappar och sensorer)
- ✅ Analoga ingångar (markfukt, temperatur)

**Säkerhet:** Motorskydd verifieras automatiskt innan pump-test

### 2. Email Test (SMTP)

Testar e-postnotifieringar:
```bash
cd /home/pi/fotbollsplan-bevattning
source .venv/bin/activate
python3 email_test.py --send-alarm-test
```

**Vad som testas:**
- ✅ SMTP-anslutning
- ✅ Test-mail
- ✅ Larm-notifieringar

### 3. Systemverifiering

Kör verifieringsskript när som helst:
```bash
cd /home/pi/fotbollsplan-bevattning
bash verify.sh
```

Detta kontrollerar:
- Python virtual environment
- Installerade beroenden
- Tjänststatus
- API-anslutning

---

## 🔍 Felsökning

### Problem: Tjänster startar inte

**Symptom:** `systemctl status` visar "failed" eller "inactive"

**Lösning:**
```bash
# Se detaljerade loggar
journalctl -u bevattning-api -n 50
journalctl -u display-manager -n 50
journalctl -u bevattning-controller -n 50

# Kör manuellt för att se fel
cd /home/pi/fotbollsplan-bevattning
source .venv/bin/activate
python3 api_main.py
```

**Vanliga orsaker:**
- Felaktig `api_.env` konfiguration
- PLC ej tillgänglig (kontrollera MODBUS_HOST)
- Python-beroenden saknas (kör `pip install -r api_requirements.txt`)

### Problem: I2C fungerar inte

**Symptom:** `i2cdetect -y 1` visar inga enheter

**Lösning:**
```bash
# Kontrollera I2C-moduler
lsmod | grep i2c

# Ladda i2c-dev modul
sudo modprobe i2c-dev

# Lägg till användare i i2c-gruppen
sudo usermod -a -G i2c pi

# Logga ut och in igen eller starta om
```

### Problem: API-nyckel fungerar inte

**Symptom:** API-anrop ger 403 Forbidden

**Lösning:**
```bash
# Redigera konfigurationsfilen
nano /home/pi/fotbollsplan-bevattning/api_.env

# Ändra API_KEY till ny nyckel
# API_KEY=din-nya-hemliga-nyckel

# Spara (Ctrl+O, Enter, Ctrl+X)

# Starta om API-tjänsten
sudo systemctl restart bevattning-api
```

### Problem: PLC-anslutning misslyckas

**Symptom:** "Modbus connection failed"

**Lösning:**
```bash
# Testa Modbus-anslutning
cd /home/pi/fotbollsplan-bevattning
source .venv/bin/activate
python3 relay_test.py --host <plc-ip>

# Kontrollera nätverksanslutning
ping <plc-ip>

# Verifiera Modbus-inställningar i api_.env
cat api_.env | grep MODBUS
```

**Vanliga orsaker:**
- Fel IP-adress (kontrollera MODBUS_HOST)
- PLC ej påslagen eller ansluten till nätverket
- Brandvägg blockerar port 502

### Problem: Tailscale fungerar inte

**Symptom:** Tailscale-status visar "stopped"

**Lösning:**
```bash
# Kontrollera Tailscale-status
sudo tailscale status

# Starta Tailscale
sudo tailscale up --ssh

# Hämta Tailscale IP
sudo tailscale ip -4

# Följ autentiseringslänken som visas
```

### Problem: Virtual environment saknas

**Symptom:** "No such file or directory: .venv"

**Lösning:**
```bash
cd /home/pi/fotbollsplan-bevattning

# Skapa virtual environment manuellt
python3 -m venv .venv

# Aktivera och installera beroenden
source .venv/bin/activate
pip install --upgrade pip
pip install -r api_requirements.txt
pip install -r display_requirements.txt
```

### Problem: PEP 668 Fel (Debian Bookworm)

**Symptom:** "error: externally-managed-environment"

**Detta borde INTE hända** om du använder `setup.sh`, men om det gör:

**Lösning:**
```bash
# Använd virtual environment (rekommenderat)
python3 -m venv .venv
source .venv/bin/activate
pip install -r api_requirements.txt

# ELLER (ej rekommenderat): Tvinga global installation
pip install --break-system-packages -r api_requirements.txt
```

---

## 📖 System 2.0 Nya Funktioner

### 1. Smart Pump Protection
Avancerad pumpsäkerhet med grace period och torrkörningsskydd:

- **Grace Period:** 25 sekunder efter pumpstart för mjukstart
- **Slangbrott-detektion:** Flöde JA, Tryck NEJ → Omedelbar stopp
- **Torrkörning-detektion:** Flöde NEJ, Tryck NEJ → Stopp efter 10 sek
- **Normal avslutning:** Flöde NEJ, Tryck JA → Mjukt stopp (slangvinda)

**Återställning efter larm:**
```bash
curl -X POST -H "X-API-Key: <din-nyckel>" http://<ip>:8000/menu/reset-error
```

### 2. Zone Exclusion (Zon-exkludering)
Inaktivera sönder zoner via API:

```bash
# Hämta zonsstatus
curl -H "X-API-Key: <nyckel>" http://<ip>:8000/zones/status

# Inaktivera zon 5 (sönder spridare)
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <nyckel>" \
  -d '{"enabled": false, "name": "Zone 5 (Sönder)"}' \
  http://<ip>:8000/zones/5/toggle

# Aktivera zon 5 igen
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: <nyckel>" \
  -d '{"enabled": true, "name": "Zone 5"}' \
  http://<ip>:8000/zones/5/toggle
```

**Inaktiverade zoner hoppas automatiskt över i Auto-läget!**

### 3. Dash Process View
Grafisk realtidsövervakning med Plotly Dash:

**Funktioner:**
- Zonöversikt med färgkodad status
- Pumpstatus (live)
- Regnprognos (nästa 24h)
- Regnhistorik (senaste 7 dagarna)
- Felvisualisering (E-stop, markfukt, regn, anti-kollision)
- Klickbara zonkontroller

**Åtkomst:**
```
http://<raspberry-pi-ip>:8050
```

### 4. Weather Integration (Open-Meteo)
Automatisk väderdata från Open-Meteo API:

- **Gratis** - ingen API-nyckel behövs
- Konfigurerbara koordinater (Håkanryd, Bromölla)
- Regnprognos (24h framåt)
- Historisk nederbörd (7 dagar bakåt)

**API-endpoint:**
```bash
curl -H "X-API-Key: <nyckel>" http://<ip>:8000/rain-forecast
```

### 5. Auto-Bevattning (Scheduler)
Daglig auto-bevattning kl 01:00 med villkorskontroller:

**Kontrollerar automatiskt:**
- BlockReason (MW73) - blockerar om != 0
- Markfukt över tröskel
- Regn över tröskel
- E-stop aktiv
- Anti-kollision

**Timer-status:**
```bash
systemctl list-timers bevattning-scheduler.timer
```

**Manuell körning (för test):**
```bash
cd /home/pi/fotbollsplan-bevattning
source .venv/bin/activate
python3 bevattning_scheduler.py --run-now --auto-start
```

---

## 🔒 Säkerhetsöverväganden

### API-nyckel
- **Byt standardnyckeln omedelbart!**
- Använd stark, slumpmässig nyckel (minst 32 tecken)
- Exponera ALDRIG API-nyckeln i public repositories

### Nätverkssäkerhet
- Kör på lokalt nätverk (LAN)
- Använd VPN (Tailscale) för fjärråtkomst
- Exponera INTE direkt på internet utan TLS/HTTPS

### Superadmin-lösenord
- Använd starkt lösenord (minst 8 tecken)
- Lösenordet hashas med bcrypt (säkert)
- `superadmin.txt` har rättigheter 600 (endast ägare kan läsa)

### SMTP-lösenord
- Använd App Passwords för Gmail med 2FA
- `api_.env` har rättigheter 600 (endast ägare kan läsa)
- Commit ALDRIG `api_.env` till git (finns i `.gitignore`)

---

## 📁 Viktiga filer och platser

```
/home/pi/fotbollsplan-bevattning/
├── api_.env                           # Konfigurationsfil (SECRETS!)
├── superadmin.txt                     # Superadmin hash (SECRETS!)
├── .venv/                             # Python virtual environment
├── api_main.py                        # FastAPI backend
├── bevattning_controller.py           # Väder-controller
├── bevattning_scheduler.py            # Auto-scheduler
├── display_manager.py                 # Display-hantering
├── pump_protection.py                 # Pump-säkerhet
├── zone_config.py                     # Zon-konfiguration
├── zone_config.json                   # Zon-status (sparad)
├── setup.sh                           # Installationsskript
├── verify.sh                          # Verifieringsskript
├── relay_test.py                      # Hårdvarutest
├── email_test.py                      # SMTP-test
└── README.md                          # Fullständig dokumentation

/etc/systemd/system/
├── bevattning-api.service             # API-tjänst
├── bevattning-controller.service      # Controller-tjänst
├── display-manager.service            # Display-tjänst
├── bevattning-scheduler.service       # Scheduler-tjänst
└── bevattning-scheduler.timer         # Scheduler-timer (01:00)
```

---

## 🆘 Support och hjälp

### Dokumentation
- **README.md** - Fullständig systemdokumentation
- **INSTALLATION.md** - Generell installationsguide
- **USER_MANAGEMENT.md** - Användarhantering
- **PIPE_NETWORK_DOCUMENTATION.md** - Rörledningsnät

### GitHub
- **Issues:** https://github.com/erikohliv/fotbollsplan-bevattning/issues
- **Discussions:** https://github.com/erikohliv/fotbollsplan-bevattning/discussions

### Loggar
```bash
# System-loggar
journalctl -u bevattning-api -f
journalctl -u display-manager -f
journalctl -u bevattning-controller -f

# Application-loggar
tail -f ~/bevattning_log.csv
```

---

## 🎓 Nästa steg

Efter lyckad installation:

1. **Konfigurera PLC-anslutning**
   - Verifiera Modbus-inställningar
   - Testa med `relay_test.py`

2. **Testa displayar**
   - Kontrollera LCD-display fungerar
   - Testa Arkadknappar

3. **Testa ventiler och pump**
   - Använd manuellt läge för varje zon
   - Verifiera inga läckage

4. **Konfigurera bevattningsschema**
   - Justera tider (Center/Hörn)
   - Ställ in tröskelvärden (regn/markfukt)

5. **Aktivera auto-bevattning**
   - Verifiera timer är aktiv
   - Övervaka första automatiska körningen

6. **Konfigurera automatisk deployment** (valfritt)
   - Se README.md sektion "Automatic System Updates"

---

**🎉 Grattis! System 2.0 är nu installerat och redo att användas!**

**OBS:** Detta är ett säkerhetskritiskt system. Testa alltid ändringar i Manual-läge innan Auto-läge aktiveras.
