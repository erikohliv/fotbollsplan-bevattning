# Installation Script Features - Quick Reference

## install_complete.py - Komplett installationsscript

### Huvudfunktioner

#### 1. WiFi-nätverkskonfiguration
- **Automatisk scanning**: Upptäcker alla tillgängliga WiFi-nätverk
- **Signalstyrka-sortering**: Visar nätverk sorterade efter bästa signal
- **Säkerhetsindikering**: Visar om nätverket är öppet eller kräver lösenord
- **Flera verktyg**: Använder nmcli (NetworkManager) eller fallback till wpa_supplicant
- **Manuell konfiguration**: Möjlighet att ange SSID manuellt om inte hittad i scan
- **Hoppa över**: Kan hoppa över WiFi-konfiguration om redan ansluten via Ethernet

#### 2. Systempaket-installation
Installerar automatiskt:
- Python 3 och utvecklingsverktyg (python3, python3-pip, python3-venv, python3-dev)
- I2C-verktyg (python3-smbus, i2c-tools)
- Nätverksverktyg (wireless-tools, wpasupplicant, network-manager)
- Versionshantering (git)
- Nätverkskommunikation (curl)
- Build-verktyg (build-essential)

#### 3. I2C-konfiguration för LCD-displayer
- Aktiverar I2C-gränssnittet via raspi-config (om tillgängligt)
- Lägger till i2c-dev kernel-modul i /etc/modules
- Laddar i2c-dev-modulen direkt
- Lägger till användaren i i2c-gruppen för åtkomsträttigheter

#### 4. Python Virtual Environment
- Skapar isolerad Python-miljö (.venv)
- Installerar api_requirements.txt (FastAPI, pymodbus, etc.)
- Installerar display_requirements.txt (smbus2 för I2C)
- Sätter korrekta ägarskap och rättigheter

#### 5. Miljövariabel-konfiguration (api_.env)
**Automatisk konfiguration av:**
- API_KEY: Säker nyckel för REST API-åtkomst
- MODBUS_HOST: PLC IP-adress
- MODBUS_PORT: Modbus TCP-port (default: 502)
- MODBUS_UNIT: Modbus Unit ID (default: 1)

**Valfri SMTP-konfiguration:**
- SMTP_HOST: E-postserver
- SMTP_PORT: SMTP-port (default: 587)
- SMTP_USER: E-postadress
- SMTP_PASS: E-postlösenord
- SMTP_FROM: Avsändare
- SMTP_TO: Mottagare (kommaseparerade)

**Säkerhet:**
- Sätter filrättigheter till 600 (endast ägaren kan läsa/skriva)
- Använder getpass() för lösenordsinmatning (visas inte på skärmen)

#### 6. Tailscale VPN
- Installerar Tailscale från officiell källa
- Konfigurerar SSH över Tailscale
- Ger säker fjärråtkomst utan portvidarebefordran
- Visar Tailscale-status och IP-adress

#### 7. systemd-tjänster
**Installerar och aktiverar:**
- bevattning-api.service - REST API backend (port 8000)
- display-manager.service - LCD-display-hantering
- bevattning-scheduler.service - Auto-bevattning kl 01:00
- bevattning-scheduler.timer - Timer för schemaläggning

**Automatisk konfiguration:**
- Uppdaterar sökvägar från /home/pi till faktisk projektplats
- Sätter korrekt användare och grupp
- Aktiverar och startar tjänsterna
- Laddar om systemd daemon

#### 8. Validering och felhantering
- Validerar IP-adresser (IPv4-format, 0-255 per oktet)
- Validerar portnummer (1-65535)
- Validerar e-postadresser (RFC-kompatibel regex)
- Validerar Modbus Unit ID (1-255)
- Timeout-hantering för alla system-kommandon
- Interaktiv felhantering med möjlighet att fortsätta eller avbryta

### Användning

```bash
# Grundläggande installation
sudo python3 install_complete.py
```

### Interaktiva prompts

Scriptet guidar användaren genom varje steg med tydliga prompter:
- **Yes/No-frågor**: Default-värde visas som [Y/n] eller [y/N]
- **Textinmatning**: Visar default-värde som [standard-värde]
- **Lösenord**: Dolt med getpass() för säkerhet
- **Val från lista**: Numrerade alternativ för WiFi-nätverk

### Status-meddelanden

Scriptet använder visuella indikatorer:
- ✓ Grön bock för lyckade operationer
- ✗ Rött kryss för fel
- ℹ Info-symbol för informativa meddelanden
- ⚠ Varningssymbol för varningar

### Felhantering och återställning

- **Timeout-skydd**: Alla kommandon har timeout (förhindrar hängningar)
- **Backup-konfiguration**: WiFi-konfiguration backas upp innan ändringar
- **Fortsätt vid fel**: Användaren kan välja att fortsätta vid icke-kritiska fel
- **Detaljerade felmeddelanden**: Visar stdout/stderr vid fel

### Säkerhetsfunktioner

1. **Root-kontroll**: Kräver sudo för systemändringar
2. **Secure permissions**: api_.env sätts till 600 (endast ägare)
3. **SUDO_USER**: Använder ursprunglig användare, inte root
4. **Lösenordsskydd**: Aldrig synliga lösenord i terminalen
5. **TLS för SMTP**: Använder STARTTLS för e-postkommunikation

### Post-installation

Efter lyckad installation:
- Visar sammanfattning av installerade komponenter
- Ger nästa steg och användbara kommandon
- Rekommenderar omstart för att aktivera alla ändringar
- Erbjuder automatisk omstart

### Testning

```bash
# Kör automatiska tester
python3 test_install_complete.py
```

Testerna validerar:
- Import av alla moduler
- Existens av alla konstanter
- Existens av alla funktioner
- Validatorer (IP, port, e-post)
- Lista över systempaket
- Script-struktur och shebang

### Filstruktur

```
install_complete.py         # Huvudinstallationsscript (1069 rader)
test_install_complete.py    # Testscript (270 rader)
INSTALLATION.md             # Detaljerad installationsguide
README.md                   # Uppdaterad med nya instruktioner
```

### Tekniska detaljer

**Programmeringsspråk**: Python 3
**Dependencies**: Endast Python standard library
**Kompatibilitet**: Debian Bookworm (Raspberry Pi OS)
**Körtid**: 5-15 minuter (beroende på nätverkshastighet)
**Diskutrymme**: ~500 MB (inkl. alla beroenden)

### WiFi-scanning implementation

Scriptet använder flera metoder för WiFi-scanning:

1. **nmcli (NetworkManager)**: Primär metod
   ```bash
   nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list
   ```

2. **iw scan**: Fallback-metod
   ```bash
   iw dev wlan0 scan
   ```

3. **Automatisk interface-detektering**: Letar efter wlan* eller wlp*

### Modular design

Funktioner är organiserade i logiska sektioner:
- Utility functions (print, input, validation)
- WiFi configuration functions
- System package installation functions
- I2C configuration functions
- Python environment setup functions
- Environment configuration functions
- Tailscale setup functions
- systemd services installation functions
- Main installation flow

### Framtida förbättringar

Möjliga förbättringar:
- Stöd för statisk IP-konfiguration
- Nätverkshastighets-test efter WiFi-anslutning
- Automatisk PLC-upptäckt på nätverket
- Backup/restore-funktionalitet
- Loggning till fil
- Progress bar för långvariga operationer
- Webhook-notifieringar vid färdig installation

---

**Version**: 1.0
**Skapad**: December 2024
**Licens**: Samma som projektet
