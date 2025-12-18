# Installation Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   FOTBOLLSPLAN-BEVATTNING - KOMPLETT INSTALLATION                  │
│   Raspberry Pi 4 - Debian Bookworm Lite                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEG 1: WiFi-konfiguration                                         │
├─────────────────────────────────────────────────────────────────────┤
│  • Skanna efter tillgängliga nätverk                                │
│  • Visa lista sorterad efter signalstyrka                           │
│  • Välj nätverk och ange lösenord                                   │
│  • Anslut med nmcli eller wpa_supplicant                            │
│  • Verifiera anslutning                                             │
│                                                                     │
│  [Kan hoppas över om redan ansluten]                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEG 2: Systempaket-installation                                   │
├─────────────────────────────────────────────────────────────────────┤
│  apt update                                                         │
│  apt install:                                                       │
│    • python3, python3-pip, python3-venv, python3-dev                │
│    • python3-smbus, i2c-tools                                       │
│    • wireless-tools, wpasupplicant, network-manager                 │
│    • git, curl, build-essential                                     │
│                                                                     │
│  [Tar 2-5 minuter beroende på nätverkshastighet]                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEG 3: I2C-aktivering                                             │
├─────────────────────────────────────────────────────────────────────┤
│  • raspi-config nonint do_i2c 0                                     │
│  • Lägg till i2c-dev i /etc/modules                                 │
│  • modprobe i2c-dev                                                 │
│  • usermod -a -G i2c <user>                                         │
│                                                                     │
│  [Krävs för LCD-display-kommunikation]                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEG 4: Python Virtual Environment                                 │
├─────────────────────────────────────────────────────────────────────┤
│  • python3 -m venv .venv                                            │
│  • pip install -r api_requirements.txt                              │
│    - fastapi, uvicorn, pymodbus, python-dotenv, requests            │
│  • pip install -r display_requirements.txt                          │
│    - smbus2, pymodbus                                               │
│  • chown -R <user>:<user> .venv                                     │
│                                                                     │
│  [Tar 3-7 minuter för alla beroenden]                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEG 5: Miljövariabel-konfiguration                                │
├─────────────────────────────────────────────────────────────────────┤
│  Skapa api_.env:                                                    │
│                                                                     │
│  API & Modbus:                                                      │
│    API_KEY=<genererad eller angiven>                                │
│    MODBUS_HOST=<PLC IP-adress>                                      │
│    MODBUS_PORT=502                                                  │
│    MODBUS_UNIT=1                                                    │
│                                                                     │
│  SMTP (valfritt):                                                   │
│    SMTP_HOST=smtp.gmail.com                                         │
│    SMTP_PORT=587                                                    │
│    SMTP_USER=<e-post>                                               │
│    SMTP_PASS=<lösenord>                                             │
│    SMTP_FROM=<avsändare>                                            │
│    SMTP_TO=<mottagare>                                              │
│                                                                     │
│  • chmod 600 api_.env  (säkerhet)                                   │
│  • chown <user>:<user> api_.env                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEG 6: Tailscale (valfritt)                                       │
├─────────────────────────────────────────────────────────────────────┤
│  • curl -fsSL https://tailscale.com/install.sh | sh                 │
│  • tailscale up --ssh                                               │
│  • Autentisera via webbläsare                                       │
│  • Få Tailscale IP-adress                                           │
│                                                                     │
│  [Ger säker fjärråtkomst utan portvidarebefordran]                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEG 7: systemd-tjänster                                           │
├─────────────────────────────────────────────────────────────────────┤
│  Installera och aktivera:                                           │
│                                                                     │
│  bevattning-api.service                                             │
│    • REST API backend (port 8000)                                   │
│    • Webb-UI för styrning                                           │
│    • Modbus-brygga till PLC                                         │
│                                                                     │
│  display-manager.service                                            │
│    • Hanterar LCD-displayer (I2C)                                   │
│    • Visar status och manuell styrning                              │
│                                                                     │
│  bevattning-scheduler.timer                                         │
│    • Triggar daglig auto-bevattning kl 01:00                        │
│                                                                     │
│  bevattning-scheduler.service                                       │
│    • Hämtar väderdata från Open-Meteo                               │
│    • Kontrollerar villkor (regn, markfukt)                          │
│    • Startar bevattning om OK                                       │
│                                                                     │
│  • systemctl daemon-reload                                          │
│  • systemctl enable <service>                                       │
│  • systemctl start <service>                                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  INSTALLATION KLAR!                                                 │
├─────────────────────────────────────────────────────────────────────┤
│  ✓ WiFi konfigurerat                                                │
│  ✓ Systempaket installerade                                         │
│  ✓ I2C aktiverat                                                    │
│  ✓ Python-miljö konfigurerad                                        │
│  ✓ Miljövariabler konfigurerade                                     │
│  ✓ Tailscale installerat (om valt)                                  │
│  ✓ systemd-tjänster aktiverade                                      │
│                                                                     │
│  Nästa steg:                                                        │
│    1. sudo reboot (rekommenderat)                                   │
│    2. Åtkomst Webb-UI: http://<ip>:8000                             │
│    3. Kontrollera tjänster: systemctl status bevattning-api         │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│  SYSTEM-ARKITEKTUR EFTER INSTALLATION                               │
└─────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │   Raspberry Pi 4    │
                    │  Debian Bookworm    │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │ bevattning-api │ │   display   │  │   scheduler    │
    │   FastAPI      │ │   manager   │  │  (timer 01:00) │
    │  (port 8000)   │ │   (I2C LCD) │  │                │
    └───────┬────────┘ └──────┬──────┘  └───────┬────────┘
            │                  │                  │
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                      ┌────────▼─────────┐
                      │  Modbus TCP/IP   │
                      │  (port 502)      │
                      └────────┬─────────┘
                               │
                      ┌────────▼─────────┐
                      │   UNIPI 1.1 PLC  │
                      │   (ST-program)   │
                      └────────┬─────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼───────┐    ┌────────▼────────┐    ┌───────▼────────┐
│  Ventiler 1-7 │    │  Pump + VFD     │    │  Markfuktgivare│
│  (Zoner)      │    │  (Siemens LOGO) │    │  (0-10V)       │
└───────────────┘    └─────────────────┘    └────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│  FJÄRRÅTKOMST (Tailscale)                                           │
└─────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐                              ┌──────────────┐
    │   Dator /   │    Tailscale VPN mesh       │ Raspberry Pi │
    │  Mobil      │◄──────────────────────────►│   (Target)   │
    │  (Kontroll) │   Krypterad tunnel          │              │
    └─────────────┘   Ingen port-forward        └──────────────┘
          │
          │  http://<tailscale-ip>:8000
          │  X-API-Key: <din-nyckel>
          │
          ▼
    ┌──────────────┐
    │   Webb-UI    │
    │   REST API   │
    │  Styrning    │
    └──────────────┘
