# Arcade Buttons - Användarinterface

## 🎮 Hårdvaruspecifikation

### Knappar
- **Antal**: 4 stycken arcade-knappar
- **I2C-kretskort**: PCF8574 eller MCP23017
- **I2C-adress**: **0x21** (kan ändras om konflikt uppstår)
- **Bus**: I2C Bus 1 (samma som LCD-display)
- **Kabel**: Delar RJ11-kabel med LCD-display (0x27) - parallellkopplad

### I2C-buss layout
```
I2C Bus 1 på RJ11-kabeln:
├── 0x20 - MCP23008 (8 reläer) - UniPi HAT
├── 0x21 - PCF8574/MCP23017 (Arcade-knappar) ⬅️ NY!
├── 0x27 - PCF8574 (LCD 20x4 Display)
├── 0x50 - EEPROM
└── 0x68 - RTC (Real-Time Clock)
```

## 🔘 Knappfunktioner

### Fysisk layout
```
    ┌──────────┐
    │  KNAPP 3 │  - OK/Select/Bekräfta
    │   (OK)   │
    └──────────┘
┌──────────┐ ┌──────────┐
│ KNAPP 1  │ │ KNAPP 2  │
│  (UPP)   │ │  (NER)   │
└──────────┘ └──────────┘
    ┌──────────┐
    │ KNAPP 4  │  - Back/Cancel/Tillbaka
    │  (BACK)  │
    └──────────┘
```

### Mappning
- **Knapp 1 (UP)**: Öka värde / Navigera upp i menyer
- **Knapp 2 (DOWN)**: Minska värde / Navigera ner i menyer
- **Knapp 3 (OK)**: Bekräfta val / Välj menyalternativ
- **Knapp 4 (BACK)**: Avbryt / Gå tillbaka i meny

## 🔒 Säkerhetslås - Unlock-sekvens

För att förhindra oavsiktlig aktivering av manuell bevattning finns ett säkerhetslås.

### Låsningsbeteende
- Systemet låses **automatiskt** efter 10 minuter utan aktivitet
- Vid låst läge: Displayen visar "🔒 LÅST" och knappar ignoreras

### Upplåsningssekvens
För att låsa upp systemet, tryck följande sekvens:

```
NER → UPP → UPP → OK
```

**Steg för steg:**
1. Tryck **NER** (Knapp 2)
2. Tryck **UPP** (Knapp 1)
3. Tryck **UPP** (Knapp 1) igen
4. Tryck **OK** (Knapp 3)

Vid korrekt sekvens: Displayen visar "✓ UPPLÅST" och systemet är aktivt i 10 minuter.

Vid felaktig sekvens: Sekvensen nollställs, försök igen från början.

## 📋 Användningsflöde

### Starta manuell bevattning
1. **Lås upp systemet**: NER → UPP → UPP → OK
2. Tryck **OK** för att öppna huvudmenyn
3. Välj "Manual" med **UPP/NER**
4. Tryck **OK** för att bekräfta
5. Välj zon (1-7) med **UPP/NER**
6. Tryck **OK** för att bekräfta
7. Ställ in tid (minuter) med **UPP/NER**
8. Tryck och **håll OK i 2 sekunder** för att starta

### Stoppa bevattning
1. Tryck **BACK** upprepade gånger för att komma till huvudmenyn
2. Välj "Stop" med **UPP/NER**
3. Tryck **OK** för att bekräfta stopp

### Avbryta operation
- Tryck **BACK** när som helst för att avbryta och gå tillbaka

## ⚙️ Installation & Konfiguration

### Hårdvara
1. **Montera arcade-knappar** i kontrollpanelen
2. **Anslut PCF8574/MCP23017-modul** till knapparna
3. **Konfigurera I2C-adress till 0x21**:
   - PCF8574: Lödbryggor A0, A1, A2 enligt datablad
   - MCP23017: Konfigurera adress-pins (vanligtvis A0-A2)
4. **Anslut till RJ11-kabel** (SDA, SCL, VCC, GND) parallellt med LCD
5. **Verifiera anslutning**:
   ```bash
   i2cdetect -y 1
   # Ska visa 0x21 i listan
   ```

### Mjukvara
Knapp-läsning implementeras i `display_manager.py`:
```python
class ArcadeButtonManager:
    def __init__(self, i2c_addr=0x21, bus_num=1):
        self.i2c_addr = i2c_addr
        # Unlock-sekvens
        self.unlock_sequence = ['down', 'up', 'up', 'ok']
        self.lock_timeout = 600  # 10 minuter
```

### Test
```bash
cd /home/kamp/fotbollsplan-bevattning
python3 test_arcade_buttons.py
```

## 🔧 Felsökning

| Problem | Lösning |
|---------|---------|
| Knappar visas inte på I2C | Kontrollera anslutning, kör `i2cdetect -y 1` |
| Fel I2C-adress | Justera lödbryggor på PCF8574-kortet |
| Knappar svarar inte | Kontrollera att `display_manager.py` är igång |
| Upplåsning fungerar inte | Kontrollera att sekvensen är: NER-UPP-UPP-OK |
| System låser sig direkt | Öka `lock_timeout` i kod (standard 600s = 10 min) |

## 📦 Hårdvarubeställning

### Rekommenderad utrustning
- **Arcade-knappar**: 30mm LED arcade buttons (4st)
- **I2C-modul**: PCF8574 eller MCP23017
- **Ledning**: CAT5/CAT6 för RJ11 (redan installerat)
- **Anslutningar**: Dupont/JST-kontakter för knappar till PCF8574

### Alternativa I2C-adresser (om 0x21 är upptagen)
- 0x22, 0x23, 0x24, 0x25, 0x26 (PCF8574)
- 0x3F (vanlig alternativ adress)

---

**Senast uppdaterad**: 2026-01-02  
**Version**: 1.0  
**Kompatibel med**: Raspberry Pi 3B+/4, UniPi 1.1
