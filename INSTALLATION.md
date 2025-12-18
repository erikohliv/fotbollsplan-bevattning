# Snabbstart - Installation Guide

## Komplett installation på Raspberry Pi 4 (Debian Bookworm Lite)

Denna guide beskriver hur du installerar fotbollsplan-bevattning på en ny Raspberry Pi 4 med Debian Bookworm Lite.

### Förutsättningar

- Raspberry Pi 4 med Debian Bookworm Lite installerat
- Tangentbord och skärm ansluten till Raspberry Pi (för första installationen)
- Eller SSH-åtkomst till Raspberry Pi
- Internet-anslutning (WiFi eller Ethernet)

### Steg 1: Grundläggande systemförberedelser

Om du använder Ethernet kan du hoppa över WiFi-konfigurationen i installationsskriptet.

Om du inte har git installerat, kör:
```bash
sudo apt update
sudo apt install -y python3 git
```

### Steg 2: Ladda ner projektet

```bash
cd ~
git clone https://github.com/erikohliv/fotbollsplan-bevattning.git
cd fotbollsplan-bevattning
```

### Steg 3: Kör komplett installation

```bash
sudo python3 install_complete.py
```

### Vad händer under installationen?

Installationsskriptet guidar dig genom följande steg:

#### 1. WiFi-konfiguration (om du inte redan är ansluten)
- Skannar efter tillgängliga WiFi-nätverk
- Visar en lista med nätverk sorterade efter signalstyrka
- Låter dig välja nätverk och ange lösenord
- Ansluter automatiskt till det valda nätverket

#### 2. Systempaket-installation
Installerar följande paket:
- Python 3 och utvecklingsverktyg
- I2C-verktyg för LCD-displayer
- Nätverksverktyg (wireless-tools, wpasupplicant, network-manager)
- Git och curl
- Build-verktyg för Python-kompilering

#### 3. I2C-aktivering
- Aktiverar I2C-gränssnittet för LCD-display-kommunikation
- Lägger till användaren i i2c-gruppen
- Konfigurerar kernel-moduler

#### 4. Python-miljö
- Skapar ett virtuellt Python-miljö (.venv)
- Installerar alla nödvändiga Python-beroenden:
  - FastAPI och uvicorn för REST API
  - pymodbus för PLC-kommunikation
  - smbus2 för I2C-kommunikation
  - Alla andra beroenden från requirements-filer

#### 5. Miljövariabel-konfiguration
Du kommer att bli tillfrågad om följande:

**API och Modbus:**
- API-nyckel (standardvärde: "byt-mig" - BYTA DETTA!)
- Modbus PLC IP-adress (t.ex. 192.168.1.100)
- Modbus port (standard: 502)
- Modbus Unit ID (standard: 1)

**SMTP E-post (valfritt):**
Om du vill ha e-postnotifieringar vid fel:
- SMTP server (t.ex. smtp.gmail.com)
- SMTP port (standard: 587)
- E-postadress och lösenord
- Mottagare för notifieringar

#### 6. Tailscale (valfritt)
- Installerar Tailscale för säker fjärråtkomst
- Konfigurerar SSH över Tailscale
- Ingen portvidarebefordran behövs

#### 7. systemd-tjänster
Installerar och aktiverar följande tjänster:
- **bevattning-api.service** - REST API och webb-UI
- **display-manager.service** - LCD-display-hantering
- **bevattning-scheduler.service** - Schemalagd auto-bevattning
- **bevattning-scheduler.timer** - Timer för daglig körning kl 01:00

### Steg 4: Starta om systemet

Efter installationen rekommenderas omstart för att aktivera alla ändringar:

```bash
sudo reboot
```

### Steg 5: Verifiera installation

Efter omstart, kontrollera att tjänsterna körs:

```bash
# Kontrollera API-tjänst
systemctl status bevattning-api

# Kontrollera display manager
systemctl status display-manager

# Kontrollera scheduler timer
systemctl status bevattning-scheduler.timer

# Lista alla timers
systemctl list-timers
```

### Steg 6: Åtkomst till systemet

#### Webb-UI
Öppna en webbläsare och gå till:
```
http://<raspberry-pi-ip>:8000
```

Du behöver använda API-nyckeln du konfigurerade i header:
```
X-API-Key: <din-api-nyckel>
```

#### Via curl
```bash
# Hämta status
curl -H "X-API-Key: <din-nyckel>" http://<raspberry-pi-ip>:8000/status

# Starta auto-bevattning
curl -X POST -H "X-API-Key: <din-nyckel>" http://<raspberry-pi-ip>:8000/command/start-auto
```

#### Via Tailscale (om installerat)
```bash
# Få Tailscale IP
sudo tailscale ip

# SSH via Tailscale
ssh pi@<tailscale-ip>

# Åtkomst till API via Tailscale
curl -H "X-API-Key: <din-nyckel>" http://<tailscale-ip>:8000/status
```

### Felsökning

#### Tjänster startar inte
```bash
# Se detaljerade loggar
journalctl -u bevattning-api -n 50
journalctl -u display-manager -n 50

# Kör manuellt för att se fel
cd /home/pi/fotbollsplan-bevattning
source .venv/bin/activate
python3 api_main.py
```

#### WiFi ansluter inte
```bash
# Kontrollera WiFi-status
nmcli device status
nmcli device wifi list

# Anslut manuellt
sudo nmcli dev wifi connect "<SSID>" password "<password>"
```

#### I2C fungerar inte
```bash
# Kontrollera I2C-enheter
sudo i2cdetect -y 1

# Lägg till användare i i2c-gruppen om det missades
sudo usermod -a -G i2c pi
```

#### API-nyckel fungerar inte
Redigera konfigurationsfilen:
```bash
nano /home/pi/fotbollsplan-bevattning/api_.env
```

Ändra `API_KEY=<din-nya-nyckel>`

Starta om API-tjänsten:
```bash
sudo systemctl restart bevattning-api
```

### Nästa steg

1. **Konfigurera PLC-anslutning**: Se till att Modbus-inställningarna är korrekta
2. **Testa displayar**: Kontrollera att LCD-displayerna fungerar
3. **Testa ventiler och pump**: Använd manuellt läge för att testa varje zon
4. **Konfigurera bevattningsschema**: Justera tider och tröskelvärden
5. **Se fullständig dokumentation**: README.md

### Viktiga filer och platser

```
/home/pi/fotbollsplan-bevattning/
├── api_.env                    # Konfigurationsfil (SÄKERHETSVARNING: innehåller secrets)
├── api_main.py                 # FastAPI backend
├── bevattning_controller.py    # Väder-controller
├── bevattning_scheduler.py     # Auto-scheduler
├── display_manager.py          # Display-hantering
├── .venv/                      # Python virtual environment
└── README.md                   # Fullständig dokumentation

/etc/systemd/system/
├── bevattning-api.service
├── bevattning-scheduler.service
├── bevattning-scheduler.timer
└── display-manager.service
```

### Support

För frågor och support, se:
- README.md för detaljerad dokumentation
- GitHub Issues för buggrapporter
- Kontakta projektägare

---

**OBS:** Håll API-nyckeln och SMTP-lösenordet hemliga. Exponera inte systemet direkt på internet utan Tailscale eller annan VPN-lösning.
