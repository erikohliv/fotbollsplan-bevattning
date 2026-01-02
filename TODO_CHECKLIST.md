# TODO Checklista - Fotbollsplan Bevattning System 2.0

**Status:** System installerat, väntar på hårdvarukompletteringar och 24V-driftsättning
**Senast uppdaterad:** 2026-01-01

---

## 🔴 KRITISKT - Före 24V-driftsättning

### Säkerhetssystem
- [ ] **Beställ 24VAC säkring med hjälpkontakt** (I12 - för övervakningssignal till PLC)
  - [ ] Beställ rätt modell med NO/NC hjälpkontakt
  - [ ] Kontrollera spänning/strömnivå (ventiler drar X ampere)
  - [ ] Planera montering i elskåp

- [ ] **Verifiera nödstopp (I03)** fungerar mekaniskt
  - [ ] Testa att maintained signal bryter korrekt
  - [ ] Verifiera att PLC reagerar (BlockReason=4)

- [ ] **Verifiera motorskydd (I10)** är anslutet korrekt
  - [ ] Kontrollera att NO/NC är rätt kopplat till GPIO 18
  - [ ] Testa med simulator om möjligt

---

## 🟡 HÅRDVARA - Installation & Uppgradering

### Användarinterface
- [ ] **Installera arkadknapparna (4st via PCF8574 på I2C)**
  - [ ] **När PCF8574-kortet anländer:**
    - [ ] Kontrollera att kortet är PCF8574 I/O Expander (beställt)
    - [ ] Läs dokumentation: `documentation/PCF8574_ARCADE_BUTTONS.md`
    - [ ] Konfigurera I2C-adress till **0x21** via A0-jumper (undvik konflikt med MCP23008 på 0x20)
    - [ ] Testa kommunikation: `i2cdetect -y 1` (ska visa 0x21)
  - [ ] **Hårdvaruinstallation:**
    - [ ] Montera fysiska arkadknappar i kontrollpanel (4st)
    - [ ] Anslut knappar till PCF8574 pins: P0(UPP), P1(NER), P2(OK), P3(BACK)
    - [ ] Installera pull-up resistorer (10kΩ) om de inte finns på kortet
    - [ ] Anslut PCF8574 till RJ11-kabel (SDA, SCL, VCC, GND) parallellt med LCD 0x27
  - [ ] **Mjukvaruuppdatering:**
    - [ ] Uppdatera `ArcadeButtonManager.read_buttons()` i `display_manager.py` med PCF8574-specifik kod
    - [ ] Implementera bitinvertering (Active LOW logik: knapp tryckt = 0)
    - [ ] Lägg till debouncing (50-100ms delay)
    - [ ] Testa knappavläsning: `python3 -c "from display_manager import ArcadeButtonManager; m = ArcadeButtonManager(); print(m.read_buttons())"`
  - [ ] **Funktionstester:**
    - [ ] Verifiera att alla 4 knappar läses korrekt individuellt
    - [ ] Testa unlock-sekvens: NER → UPP → UPP → OK
    - [ ] Verifiera lock timeout (10 min inaktivitet)
    - [ ] Testa menynavigering med Display 1
  - [ ] Se **ARCADE_BUTTONS.md** och **documentation/PCF8574_ARCADE_BUTTONS.md**

### Sensorer
- [ ] **DI13 & DI14 (GPIO 27 & 22)** - Beslut: Installera eller dokumentera som "reserved"?
  - Kräver lödning eller ytterligare koppling
  - Bestäm användningsområde (extra säkerhet? temperatur?)

### Analog Input Kalibrering
- [ ] **ADC (ADS1115) - Testa när 24V är på**
  - [ ] AI1 (Markfukt 0-10V) - verifiera skalning 0-100%
  - [ ] AI2 (Jordtemperatur 0-10V) - kalibrera temperaturomvandling
  - [ ] Justera voltage scaling i `unipi_modbus_server.py` om behövs

---

## 📋 DOKUMENTATION - Manualer & Scheman

### Hårdvarudokumentation
- [ ] **Uppdatera dokumentation med rätt manualer och uppgifter om all hårdvara**
  - [ ] UniPi 1.1 HAT - länk till officiell manual
  - [ ] Raspberry Pi 4 Model B - specifikationer
  - [ ] MCP23008 (Reläer) - datablad och koppling
  - [ ] ADS1115 (ADC) - datablad och kalibrering
  - [ ] PCF8574 (Display & Knappar) - I2C-adresser
  - [ ] LCD 20x4 - specifikationer
  - [ ] Mjukstartare - modell och parametrar
  - [ ] Solenoid-ventiler - 24VAC specifikationer
  - [ ] Pump - typ, effekt, flöde
  - [ ] Tryckvakt - tryckområde, NO/NC
  - [ ] Flödesvakt - flödesområde, NO/NC
  - [ ] Markfuktsensor - typ, 0-10V mappning
  - [ ] Jordtemperatur-sensor - typ, 0-10V mappning

- [ ] **Skapa kopplingsschema (Electrical Wiring Diagram)**
  - [ ] Elskåp layout
  - [ ] 230VAC huvudmatning
  - [ ] 24VDC PSU → PLC, sensorer
  - [ ] 24VAC transformer → ventiler
  - [ ] Reläkoppling R1-R8
  - [ ] Digital input DI1-DI12 (med DI13-14 reserved)
  - [ ] Analog input AI1-AI2
  - [ ] Säkringar och skydd
  - [ ] Jordning och PE
  - Filformat: PDF + editerbara källor (KiCad/Fritzing/Draw.io)

- [ ] **Uppdatera vattenledningarna (Pipe Network Documentation)**
  - [ ] Verifiera befintlig `PIPE_NETWORK_DOCUMENTATION.md`
  - [ ] Lägg till fysiska mått (rördiameter, längder)
  - [ ] Dokumentera ventilplaceringar
  - [ ] Zon-täckning (vilka munstycken per zon)
  - [ ] Flödesberäkningar (L/min per zon)
  - [ ] Tryckförlust-kalkyl
  - [ ] Vintersäkring (dränering)

### Systemarkitektur
- [ ] **Dokumentera Python + .st hybrid-arkitektur**
  - [ ] Tydliggör ansvar: Python=beslut, .st=sekvens
  - [ ] Anti-vattenslag-logik (OpenDelay/CloseDelay)
  - [ ] Modbus register-mappning
  - [ ] State machine (Steg 0, 10, 20, 22, 30)
  - [ ] Varning: "TA ALDRIG BORT .st-FILEN UTAN ATT IMPLEMENTERA SEKVENSLOGIK I PYTHON"

- [ ] **Skapa en Wiki (GitHub Wiki eller separat)**
  - [ ] Kom igång (Quick Start Guide)
  - [ ] Installation från scratch
  - [ ] Användarmanualer (LCD-interface, API, Dash)
  - [ ] Felsökning (Troubleshooting)
  - [ ] Underhåll (Vinter/Sommar)
  - [ ] API-referens
  - [ ] Modbus-register referens
  - [ ] FAQ

### Operationell Dokumentation
- [ ] **Lägg upp all annan dokumentation**
  - [ ] Driftkort (checklista för säsongsstart)
  - [ ] Underhållsschema (filter, sensorkalibrering)
  - [ ] Larmhantering (email-lista, eskaleringsprocess)
  - [ ] Backup-rutin (config-filer, databaser)
  - [ ] Logganalys (var hittar man loggar, hur tolka dem)
  - [ ] Kontaktinformation (elinstallatör, leverantörer)

---

## ⚙️ SYSTEM - Konfiguration & Testing

### Python-kod
- [ ] **Implementera arkadknapps-läsning i `display_manager.py`**
  - [ ] Läs PCF8574 via I2C
  - [ ] Mappa knappar till funktioner (Select Zone, Start, Stop, Menu?)
  - [ ] Integrera med befintlig LCD-logik

- [ ] **Förbättra `pump_protection.py`**
  - [ ] Kalibrera SLANGBROTT_FLOW_THRESHOLD efter verklig pump
  - [ ] Kalibrera TORRKORNING_PRESSURE_THRESHOLD
  - [ ] Testa med olika feltillstånd

- [ ] **Zone Config integration**
  - [ ] Verifiera `zone_config.py` fungerar med .st-fil
  - [ ] Testa att inaktiverade zoner skippas korrekt

### Email & Notifikationer
- [ ] **Testa email-notiser vid alla larmtyper**
  - [ ] Slangbrott (BlockReason=11)
  - [ ] Torrkörning (BlockReason=12)
  - [ ] Tryckvakt (BlockReason=5)
  - [ ] Flödesvakt (BlockReason=6)
  - [ ] Motorskydd (BlockReason=7)
  - [ ] Mjukstartare fel (BlockReason=8)
  - [ ] 24VDC säkring (BlockReason=9)
  - [ ] 24VAC säkring (BlockReason=10)

### PLC-program
- [ ] **Verifiera att .st-filen kan laddas (om behövs)**
  - Alternativt: Bekräfta att Python-koden KÖR .st-logiken via Modbus (nuvarande läge)
  - [ ] Testa att Remote_Command puls startar sekvens
  - [ ] Verifiera att Steg 10→20→22→30 körs korrekt

---

## 🔋 24V POWER-ON - Driftsättning

### Pre-flight Check
- [ ] **Visuell inspektion av elkopplingar**
  - [ ] Alla skruvplintar åtdragna
  - [ ] Ingen lös ledning
  - [ ] PE-ledare korrekt anslutna
  - [ ] Säkringar rätt dimensionerade

- [ ] **Mät spänningar FÖRE belastning**
  - [ ] 24VDC PSU: Exakt spänning (23-25V OK)
  - [ ] 24VAC transformer: Mät AC-spänning

### Power-on Sekvens
- [ ] **Steg 1: Sätt på 24VDC**
  - [ ] Verifiera att PLC får spänning
  - [ ] Kontrollera att digitala inputs läses korrekt
  - [ ] Testa att analog inputs visar värden (AI1, AI2)

- [ ] **Steg 2: Sätt på 24VAC (ventiler)**
  - [ ] Sätt på EN ventil i taget via API/Modbus
  - [ ] Lyssna efter klickljud från solenoid
  - [ ] Verifiera att relay LED tänds (R1-R7)
  - [ ] Ingen pump igång vid test!

- [ ] **Steg 3: Testa pump UTAN vatten**
  - [ ] Kort test (5 sekunder) med pump isolerad
  - [ ] Verifiera att mjukstartare startar
  - [ ] Kolla att motorskydd inte löser ut
  - [ ] Kolla att pump stängs av korrekt

- [ ] **Steg 4: Testa med vatten (en zon)**
  - [ ] Öppna ventil Zon 1
  - [ ] Vänta OpenDelay (5s)
  - [ ] Starta pump
  - [ ] Verifiera flöde visuellt
  - [ ] Kontrollera tryckvakt aktiverar
  - [ ] Kontrollera flödesvakt aktiverar
  - [ ] Stoppa efter 1 minut
  - [ ] Verifiera CloseDelay (10s) innan ventil stängs

- [ ] **Steg 5: Full sekvens (alla zoner)**
  - [ ] Kör auto-sekvens Zon 1→7
  - [ ] Övervaka pump-safety under hela körningen
  - [ ] Verifiera övergångar mellan zoner
  - [ ] Kontrollera att PauseDelay fungerar

### Post-power Testing
- [ ] **Säkerhetstest**
  - [ ] Tryck nödstopp → verifiera omedelbar pump-stopp
  - [ ] Simulera tryckvakt-fel → verifiera pump-stopp + BlockReason=5
  - [ ] Simulera flödesvakt-fel → verifiera pump-stopp + BlockReason=6
  - [ ] Testa email-notis vid larm

- [ ] **Långtidstest**
  - [ ] Kör bevattning 3 dagar i rad
  - [ ] Analysera loggar för anomalier
  - [ ] Verifiera att scheduler (cron/systemd timer) fungerar
  - [ ] Kontrollera att vinterläge blockerar (1 nov - 31 mars)

---

## 🌐 REMOTE ACCESS & MONITORING

- [x] **Tailscale konfigurerat** ✅
  - [x] Tailscale IP: 100.124.254.103
  - [x] SSH-åtkomst fungerar
  - [x] API tillgänglig (port 8000)
  - [x] Dash tillgänglig (port 8050)

- [ ] **Skapa Dashboard för övervakning**
  - [ ] Realtidsgraf: Tryck, Flöde, Markfukt
  - [ ] Larmhistorik senaste 30 dagarna
  - [ ] Systemstatus (uptime, CPU, minne)
  - [ ] Bevattningsstatistik (totala timmar per zon)

- [ ] **Backup & Recovery**
  - [ ] Automatisk backup av config-filer till GitHub
  - [ ] Backup av loggar (bevattning_log.csv, system logs)
  - [ ] SD-kort image (full system backup)
  - [ ] Recovery-instruktioner om SD-kort kraschar

---

## 📝 ANVÄNDARMANUALER

- [ ] **LCD-interface Manual**
  - [ ] Hur välja zon
  - [ ] Hur starta/stoppa manuellt
  - [ ] Tolka status-meddelanden
  - [ ] Tolka felkoder (BlockReason 1-12)

- [ ] **API Manual (för tekniker)**
  - [ ] Endpoints: /zones, /schedule, /manual-start
  - [ ] Autentisering (API-key)
  - [ ] Exempel: curl/Python-script

- [ ] **Underhållsmanual**
  - [ ] Veckovis: Visuell kontroll
  - [ ] Månadsvis: Testa larm, rengör filter
  - [ ] Säsongsvis: Sensorkalibrering, vintersäkring
  - [ ] Årligen: Elinspektion, ventilservice

---

## 🎯 FRAMTIDA FÖRBÄTTRINGAR (Backlog)

- [ ] **Väderprognosintegration**
  - [ ] Auto-justering av tid baserat på prognos 3 dagar fram
  - [ ] Sms-notis vid oväder

- [ ] **Markfuktsensor-array**
  - [ ] Flera sensorer per zon för bättre precision
  - [ ] Automatisk kalibrering mot väder

- [ ] **Energioptimering**
  - [ ] Kör bevattning under låglast-tid (natt) för billigare el

- [ ] **Webgränssnitt för slutanvändare**
  - [ ] Mobilvänlig dashboard
  - [ ] Schema-redigering via GUI
  - [ ] Historik med grafer

- [ ] **OTA-uppdateringar**
  - [ ] Git pull + systemctl restart via webb-UI
  - [ ] Versionshantering

---

## ✅ KLART (Dokumentation)

- [x] Python-kod installerad (System 2.0)
- [x] Systemd-services konfigurerade
- [x] Modbus TCP-server fungerar (unipi_modbus_server.py)
- [x] Email-notiser testade
- [x] Tailscale konfigurerat
- [x] SMTP_SETUP_GUIDE.md skapad
- [x] UNIPI_GPIO_MAPPING.md skapad
- [x] TAILSCALE_ACCESS.md skapad
- [x] requirements.txt uppdaterad
- [x] Venv konfigurerat
- [x] User management implementerat (superadmin)

---

## 📞 KONTAKTER & LEVERANTÖRER (Fyll i)

| Typ | Företag/Person | Telefon | Email | Anteckningar |
|-----|----------------|---------|-------|--------------|
| Elinstallatör | | | | |
| VVS | | | | |
| UniPi support | | | | |
| Pump-leverantör | | | | |
| Sensor-leverantör | | | | |

---

**VIKTIG PÅMINNELSE:**
⚠️ **TA ALDRIG BORT .st-FILEN** utan att först implementera full sekvenslogik (OpenDelay, CloseDelay, state machine) i Python. Risk för vattenslag!
