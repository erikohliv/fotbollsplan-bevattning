# Display 1 - Meny och Interaktivitet

## 📋 Översikt

Display 1 (20x4 LCD) har förbättrats med fullständig menyhantering via 4 arkadknappar.

**Version:** 2.1  
**Datum:** 2026-01-02

---

## 🎮 Arkadknappar

### Hårdvara
- **Chip:** PCF8574 I/O Expander
- **I2C-adress:** 0x21 (konfigurerbar)
- **Logik:** Active LOW (knapp tryckt = 0)

### Knappfunktioner
```
P0 (bit 0): UPP     - Navigera upp / Öka värde
P1 (bit 1): NER     - Navigera ner / Minska värde
P2 (bit 2): VÄNSTER - Tillbaka / Avbryt
P3 (bit 3): OK      - Bekräfta / Öppna meny
```

---

## 🔐 Säkerhetsfunktioner

### 1. Unlock-Sekvens
**Problemet:** Förhindra oavsiktliga knapptryckningar  
**Lösningen:** Kräv sekvens för att aktivera knappar

**Sekvens:**
```
NER → UPP → UPP → OK (inom 5 sekunder)
```

**Display visar:**
```
   🔒 LÅST 🔒
 
 Tryck sekvens:
 NER→UPP→UPP→OK
```

**Efter upplåsning:**
```
 
   ✓ UPPLÅST
 
 Aktiv i 10 min
```

### 2. Auto-Lock Timeout
- **Timeout:** 10 minuter inaktivitet
- **Varning:** Visas vid 60 sekunder kvar
- **Återställning:** Tryck valfri knapp för att förlänga

**Timeout-varning:**
```
  AUTO-LOCK OM
    60 SEK
 Tryck knapp för
   att förlänga
```

### 3. Låsindikator
- **🔓** = Upplåst (knappar aktiva)
- **🔒** = Låst (knappar inaktiva)

Visas i övre högra hörnet på STATUS-vy:
```
Auto Z:2/2 PUMP:ON🔓
```

---

## 📊 Auto-Roterande Vyer (5st)

När systemet är i AUTO_ROTATE-läge roteras vyerna automatiskt var 4:e sekund.

### View 1: STATUS (med progressbar!)
```
Auto Z:2/2 PUMP:ON🔓
Stage:3 [██████----]
T:18C M:45% R:2mm
Status: OK
```

**Nytt:**
- ✅ Progressbar för sekvens (Stage 0-30 → 0-100%)
- ✅ Låsindikator (🔒/🔓)

### View 2-5: (Oförändrade)
- BLOCK CONDITIONS
- PUMP STATE
- CONNECTIVITY
- MODE STATUS

---

## 🍔 Menystruktur

### Huvudmeny
```
  HUVUDMENY
 
> Starta Zon
  Stoppa Pump
  Användarstyrning
```

**Navigation:**
- **UPP/NER:** Byt markering (scrollar om fler än 2 items)
- **OK:** Välj alternativ
- **VÄNSTER:** Tillbaka till STATUS

**Användarstyrning:**
- Välj "Användarstyrning" i huvudmenyn
- Välj "Aktivera" eller "Deaktivera"
- När aktivt kan alla inloggade användare styra systemet via webbgränssnitt utan API-nyckel

---

### Starta Zon → Zonval
```
   VÄLJ ZON
 
> Zon 1
  Zon 2
```

**Navigation:**
- **UPP/NER:** Välj zon (1-7)
- **OK:** Nästa (Tidsval)
- **VÄNSTER:** Tillbaka

---

### Starta Zon → Tidsval
```
   VÄLJ TID
 
  10 minuter
 UPP/NER ändra
```

**Navigation:**
- **UPP:** Öka tid (+5 min, max 60)
- **NER:** Minska tid (-5 min, min 5)
- **OK:** Nästa (Schema)
- **VÄNSTER:** Tillbaka

---

### Starta Zon → Schemaläggning
```
  STARTA ZON
 
> Starta Nu
  Schemalägg
```

**Navigation:**
- **UPP/NER:** Byt alternativ
- **OK:** 
  - Om "Nu": Gå till bekräftelse
  - Om "Schemalägg": Välj tid
- **VÄNSTER:** Tillbaka

---

### Starta Zon → Schematid (om schemalagt)
```
  VÄLJ STARTTID
 
    06:00
UPP/NER ändra tim
```

**Navigation:**
- **UPP:** Öka timme (0-23)
- **NER:** Minska timme
- **OK:** Nästa (bekräftelse)
- **VÄNSTER:** Tillbaka

**TODO:** Lägg till minutval i framtiden

---

### Starta Zon → Bekräftelse
```
 STARTA ZON 2?
   10 min
[OK] Starta
[←] Avbryt
```

**Om schemalagt:**
```
 STARTA ZON 2?
  Kl 06:00
[OK] Starta
[←] Avbryt
```

**Navigation:**
- **OK:** STARTA! → Skriv till Modbus
- **VÄNSTER:** Avbryt

---

### Bekräftelse efter start
```
 ✓ ZON 2 STARTAR
 
  Återgår till
    status...
```

Visas i 3 sekunder, sedan tillbaka till AUTO_ROTATE.

---

## ⚡ Snabbstart

**Funktion:** Starta senast valda zon utan att gå genom menyn

**Hur:**
1. Från STATUS-vy
2. Håll **OK** i 3 sekunder

**Display visar:**
```
   SNABBSTART
 
 Startar Zon 2
    i 3 sek...
```

**Countdown:** 3 → 2 → 1 → START!

**Om du släpper knappen:** Snabbstart avbryts

---

## ⚠️ Felhantering

### E-Stop Fel (med reset-instruktioner!)
```
    ⚠️ LARM ⚠️
  E-STOP AKTIV
1. Tryck RESET-knapp
2. Bekräfta i meny
```

**Nytt:** Tydliga instruktioner för HUR man återställer!

### Andra Fel
```
    ⚠️ LARM ⚠️
   REGN (2mm)
 
Tryck OK för meny
```

**Felkoder:**
- `OK` - Inga fel
- `REGN` - Regntröskel överskriden
- `FUKTIG` - Markfukt för hög
- `KOLLISION` - Anti-kollision aktiv
- `E-STOP` - Nödstopp aktivt

---

## 🔧 Implementation

### Nya Klasser och Enums

```python
class MenuState(IntEnum):
    AUTO_ROTATE = 0        # Auto-roterande vyer (default)
    MAIN_MENU = 1          # Huvudmeny
    ZONE_SELECT = 2        # Välj zon
    TIME_SELECT = 3        # Välj tid
    SCHEDULE_SELECT = 4    # Start nu eller schemalägg
    SCHEDULE_TIME = 5      # Välj starttid
    CONFIRM = 6            # Bekräfta
    RUNNING = 7            # Körning pågår
    ERROR_VIEW = 8         # Felmeddelande
    UNLOCK_VIEW = 9        # Unlock-prompt
    TIMEOUT_WARNING = 10   # Timeout-varning
```

### Nya Metoder i ArcadeButtonManager

```python
def read_buttons_debounced(delay=0.05) -> dict
def wait_for_button_release()
def get_button_press() -> str  # Returnerar 'up'/'down'/'left'/'ok'
def check_unlock_sequence() -> bool
def get_time_until_lock() -> int
def reset_activity_timer()
```

### Nya Metoder i Display1Manager

```python
def render_progressbar(percent, width) -> str
def handle_quick_start() -> bool
def start_zone(zone, duration_minutes)
def stop_pump()
def handle_menu_navigation()  # Huvudloop

# Rendering methods
def _render_status_view_enhanced(status)
def _render_error_view(status)
def _render_unlock_view()
def _render_timeout_warning()
def _render_main_menu()
def _render_zone_select()
def _render_time_select()
def _render_schedule_select()
def _render_schedule_time()
def _render_confirm()
def _render_running(status)
def _render_unlocked_confirmation()
```

---

## 📊 Användningsflöde

### Scenario 1: Snabbstart (snabbast)
```
STATUS-vy → Håll OK 3s → ZON STARTAR
```

### Scenario 2: Välj zon och tid (normalt)
```
STATUS-vy → OK → HUVUDMENY → 
  Starta Zon → OK → 
  ZONVAL (välj med UPP/NER) → OK →
  TIDSVAL (justera med UPP/NER) → OK →
  SCHEMA (välj "Nu") → OK →
  BEKRÄFTA → OK → 
  ZON STARTAR
```

### Scenario 3: Schemalägg bevattning (avancerat)
```
STATUS-vy → OK → HUVUDMENY → 
  Starta Zon → OK → 
  ZONVAL (välj zon) → OK →
  TIDSVAL (välj tid) → OK →
  SCHEMA (välj "Schemalägg") → OK →
  VÄLJ STARTTID (t.ex. 06:00) → OK →
  BEKRÄFTA → OK → 
  SCHEMALAGT!
```

### Scenario 4: Stoppa pump
```
STATUS-vy → OK → HUVUDMENY → 
  NER (markera "Stoppa Pump") → OK → 
  PUMP STOPPAD
```

---

## 🧪 Testning

### Test 1: Unlock-sekvens
```bash
cd /home/kamp/fotbollsplan-bevattning
python3 -c "
from display_manager import ArcadeButtonManager
m = ArcadeButtonManager(0x21)
print('Tryck: NER → UPP → UPP → OK')
if m.check_unlock_sequence():
    print('✅ UNLOCKED!')
else:
    print('❌ Failed')
"
```

### Test 2: Knappavläsning
```bash
python3 -c "
from display_manager import ArcadeButtonManager
m = ArcadeButtonManager(0x21)
while True:
    buttons = m.read_buttons_debounced()
    print(f'UP:{buttons[\"up\"]} DN:{buttons[\"down\"]} L:{buttons[\"left\"]} OK:{buttons[\"ok\"]}')
    time.sleep(0.2)
"
```

### Test 3: Menynavigering
```bash
# Starta display manager med menyloop
python3 display_manager.py
```

---

## 🚀 Deployment

### 1. Uppdatera display_manager.py
```bash
cd /home/kamp/fotbollsplan-bevattning
# Metoder från display_menu_enhancements.py är redan inkluderade
```

### 2. Testa utan hårdvara (mock)
```bash
python3 test_display_manager.py
```

### 3. Testa med PCF8574 (när den anländer)
```bash
# Verifiera I2C
i2cdetect -y 1  # Ska visa 0x21

# Starta display manager
systemctl restart display-manager.service

# Kolla loggar
journalctl -u display-manager.service -f
```

---

## 📋 Checklista

- [x] PCF8574-kod implementerad
- [x] Unlock-sekvens
- [x] Auto-lock timeout
- [x] Timeout-varning
- [x] Progressbar
- [x] Snabbstart (håll OK 3s)
- [x] Huvudmeny
- [x] Zonval
- [x] Tidsval
- [x] Schemaläggning
- [x] E-stop reset-instruktioner
- [ ] Test med verklig hårdvara (väntar på PCF8574)
- [ ] Integration med bevattning_controller.py
- [ ] Användartest på fotbollsplan

---

## 💡 Framtida Förbättringar

1. **Minutval vid schemaläggning** (nu endast timme)
2. **Historik** - Visa senaste 5 bevattningar
3. **Statistik** - Total vattenmängd per zon
4. **Underhåll** - Påminnelse om filter/sensorkalibrering
5. **Väder-prognos** - Visa kommande regn från OpenMeteo
6. **Multispråk** - Svenska + Engelska

---

**Senast uppdaterad:** 2026-01-02  
**Författare:** GitHub Copilot + User  
**Status:** Redo för hårdvarutest
