# Hardware Refactor V2 - Hårdvarumappning och Säkerhetsuppdateringar

## Översikt
Detta dokument beskriver den uppdaterade hårdvarumappningen för fotbollsplans bevattningssystem efter refactoring V2.

## Digital Inputs (PLC)

| Pin | ID | Variabel | Funktion | Typ | Beskrivning |
|-----|-----|----------|----------|-----|-------------|
| %IX0.0 | I01 | Button_Stop | Stopp-knapp S202 | Momentary | Stoppar pågående körning |
| %IX0.1 | I02 | Button_Start | Start-knapp S201 | Momentary | Startar sekvens |
| %IX0.2 | I03 | EStop_NC | Nödstopp S205 | Maintained | KRITISK - Bryter hela systemet (BlockReason=4) |
| %IX0.3 | I04 | Button_Reset | Reset-knapp S203 | Momentary | Återställer larm och fel |
| %IX0.4 | I05 | Button_Set_Auto | Auto-läge S204 | **PULSE/MOMENTARY** | Växlar till Auto-läge (latched i PLC) |
| %IX0.5 | I06 | Button_Set_Manual | Manual-läge S204 | **PULSE/MOMENTARY** | Växlar till Manual-läge (latched i PLC) |
| %IX0.6 | I07 | Flow_Switch | Flödesgivare | Digital | Detekterar flöde (torrkörningsskydd) |
| %IX0.7 | I08 | Soft_Starter_Fault | Mjukstartare Signal | Digital | Fault-signal från mjukstartare (BlockReason=8) |
| %IX1.0 | I09 | Switch_Pressure | Tryckgivare | Digital | Detekterar tryck (läckageskydd) |
| %IX1.1 | I10 | Motor_Protection | Motorskydd Q1 | Digital | **KRITISKT LARM** - Motorskydd utlöst (BlockReason=7) |

## Digital Outputs (Relays)

| Pin | ID | Variabel | Funktion | Anslutning |
|-----|-----|----------|----------|------------|
| %QX0.0 | R1 | Valve_1 | Zon 1 ventil | Solenoid 24V |
| %QX0.1 | R2 | Valve_2 | Zon 2 ventil | Solenoid 24V |
| %QX0.2 | R3 | Valve_3 | Zon 3 ventil | Solenoid 24V |
| %QX0.3 | R4 | Valve_4 | Zon 4 ventil | Solenoid 24V |
| %QX0.4 | R5 | Valve_5 | Zon 5 ventil | Solenoid 24V |
| %QX0.5 | R6 | Valve_6 | Zon 6 ventil | Solenoid 24V |
| %QX0.6 | R7 | Valve_7 | Zon 7 ventil | Solenoid 24V |
| %QX0.7 | R8 | Pump_Enable | Pumpstyrning | Relä till Mjukstartare |

## Analog Inputs

| Pin | ID | Variabel | Funktion | Range | Beskrivning |
|-----|-----|----------|----------|-------|-------------|
| %IW0 | A1 | Analog_Markfukt_Raw | Markfuktgivare | 0-10V | Skalas till 0-100% i PLC (MW30) |
| %IW1 | A2 | Analog_Temp_Raw | Jordtemperatur | 0-10V | Temperaturgivare, råvärde i MW37 |

**OBS:** Markfukt och temperatur kommer från samma fysiska sensor-enhet men använder separata analog-kanaler.

## I2C-enheter

### Display 1 (D1) - System Status Display
- **Typ:** 20x4 LCD
- **I2C-adress:** 0x27 (standard, konfigurerbar)
- **Funktion:** Visar systemstatus, aktiv zon, återstående tid, larm
- **Uppdateringsfrekvens:** Auto-rotating views var 5:e sekund

### Arcade Buttons (Nya)
- **Typ:** 4 st arcade-knappar på I2C
- **I2C-adress:** 0x20 (default, kan konfigueras beroende på hårdvara)
  - **OBS:** 0x20 är en vanlig adress för PCF8574 I/O expanders. Om konflikt uppstår, använd alternativ adress (t.ex. 0x21-0x27 beroende på hårdvara).
  - **Verifikation:** Kör `sudo i2cdetect -y 1` för att se upptagna adresser.
- **Knappar:**
  - Button 1: Upp/Öka
  - Button 2: Ner/Minska
  - Button 3: OK/Välj
  - Button 4: Tillbaka/Avbryt
- **Funktion:** Navigera menyer på Display 1, välja zoner och tider
- **Implementation:** Se `ArcadeButtonManager` klass i `display_manager.py` - läslogik är placeholder och måste anpassas till faktisk hårdvara.

### Display 2 (D2) - **BORTTAGEN**
Display 2 har tagits bort från systemet. All användarinteraktion sker nu via Display 1 och de nya arcade-knapparna.

## Auto/Manual Latch Logic

### Problem
I05 och I06 är **PULSE/MOMENTARY** inputs (knappen sluter endast när den trycks, ingen maintained position).

### Lösning - Latched State i PLC
PLC-koden implementerar latch-logik med edge-detection:

```structured-text
(* Detektera rising edge på Auto-knapp (I05) *)
IF Button_Set_Auto AND NOT Prev_Button_Set_Auto THEN
  System_Mode_Latched := 1;  (* 1 = Auto *)
  ModeIsAuto := TRUE;
  ModeRegister := 1;
END_IF;
Prev_Button_Set_Auto := Button_Set_Auto;

(* Detektera rising edge på Manual-knapp (I06) *)
IF Button_Set_Manual AND NOT Prev_Button_Set_Manual THEN
  System_Mode_Latched := 0;  (* 0 = Manual *)
  ModeIsAuto := FALSE;
  ModeRegister := 0;
END_IF;
Prev_Button_Set_Manual := Button_Set_Manual;
```

**Resultat:** Tryck på I05 → systemet är i Auto-läge tills I06 trycks (och vice versa).

## Motorskydd och Säkerhetslogik

### Motor Protection (I10) - KRITISKT LARM
När motorskydd Q1 utlöser (I10 hög):
1. **OMEDELBAR ÅTGÄRD:** Pump stoppas direkt (`Signal_Pump := FALSE`)
2. **BlockReason:** Sätts till 7 (Motorskydd utlöst)
3. **EventMask:** Bit 5 sätts (motorskydd-flagga)
4. **Sekvens:** Stoppas och nollställs
5. **Reset:** Kräver fysisk åtgärd + reset-knapp när motorskydd inte längre är aktivt

### Soft Starter Fault (I08)
När mjukstartaren rapporterar fel (I08 hög):
1. **OMEDELBAR ÅTGÄRD:** Pump stoppas direkt
2. **BlockReason:** Sätts till 8 (Mjukstartare fel)
3. **Reset:** Kan återställas med reset-knapp när felet är åtgärdat

### Emergency Stop (I03)
Nödstopp är maintained signal (håller låg när inte tryckt, NC-kontakt):
1. **BlockReason:** 4 (E-stop aktiv)
2. **Reset:** E-stop måste fysiskt återställas innan systemet kan köras igen

## Modbus Register Mapping

### Nya/Uppdaterade Register

| Register | Namn | Beskrivning | R/W |
|----------|------|-------------|-----|
| MW30 | Markfukt | Markfukt 0-100% (från A1 eller Python) | R/W |
| MW37 | Soil_Temp_Raw | Jordtemperatur råvärde från A2 (0-27648) | R |
| MW60 | ModeRegister | Auto/Manual latched state (1=Auto, 0=Manual) | R |
| MW64 | MenuButtonsReg | **DEPRECATED** - Arcade buttons på I2C istället | R |
| MW72 | EventMaskReg | Event mask: bit5=Motorskydd (bit0-4 tidigare) | R |
| MW73 | BlockReasonReg | Block reason: 7=Motorskydd, 8=Soft starter fault | R |

### Block Reason Codes (MW73)

| Kod | Beskrivning | Åtgärd |
|-----|-------------|--------|
| 0 | OK - Inget fel | - |
| 1 | Regn över tröskel | Vänta på torrare väder |
| 2 | Markfukt över tröskel | Vänta tills jorden torkar |
| 3 | Anti-kollision / Pump upptagen | Vänta tills sekvens är klar |
| 4 | E-stop aktiv | Återställ E-stop fysiskt |
| 5 | Tryckvakt fel | Kontrollera tryck, reset |
| 6 | Flödesvakt fel | Kontrollera vattenförsörjning, reset |
| 7 | **Motorskydd utlöst** | **KRITISK - kontrollera motor och el-installation** |
| 8 | Mjukstartare fel | Kontrollera mjukstartare, reset |

## Säkerhetsöverväganden

### Prioritering av Larm
1. **KRITISKT (BlockReason 4, 7):** E-stop, Motorskydd → Kräver fysisk åtgärd
2. **HÖGT (BlockReason 5, 6, 8):** Tryck-, flödes-, mjukstartare-fel → Kräver undersökning och reset
3. **MEDEL (BlockReason 1, 2):** Väderrelaterat → Automatisk återställning när villkor OK
4. **LÅGT (BlockReason 3):** Anti-kollision → Automatisk återställning

### Reset-logik
- **Reset-knapp (I04):** Återställer alla fel **utom** E-stop och motorskydd om de fortfarande är aktiva
- **MW82 (ErrorReset):** Modbus-register för reset via API/Python
- **Villkor:** Motor protection måste vara inaktiv innan reset godkänns

## Användargränssnitt

### Security Lock (Knapplås)
- **Timeout:** 10 minuter inaktivitet
- **Upplåsning:** Button-sequence (konfigurerbar av användare)
- **Funktion:** Förhindrar oavsiktlig styrning

### Display 1 Views
1. **STATUS:** Aktuell zon, pump, sekvens
2. **BLOCK_CONDITIONS:** Larm och blockeringsorsaker
3. **PUMP_STATE:** Pumpstatus och säkerhetsgivare
4. **CONNECTIVITY:** Modbus-anslutning, heartbeat
5. **MODE_STATUS:** Auto/Manual, Lokal/Fjärr

### Arcade Button Navigation
- **Menystruktur:** OVERVIEW → MODE → ZONE → TIME → CONFIRM
- **Bekräftelse:** Håll OK-knapp i 2 sekunder för att starta

## Väder och Fallbacks

### OpenMeteo Integration
- **Location:** Håkanryd, Bromölla (koordinater konfigurerbara)
- **API:** Gratis, inget API-nyckel behövs
- **Data:** Regnprognos 24h, historisk nederbörd 7 dagar

### Fallback Logic
1. **API nere:** Prompt användare: "Run on Sensor?" eller "Force Ready?"
2. **Sensor fail:** Manuell beslutsprompt
3. **Säsong:** Ingen bevattning på vintern, varning för blowout senast 31 oktober

## Installation och Test

### Verifiera Hårdvaruanslutningar
```bash
# Kontrollera I2C-enheter
sudo i2cdetect -y 1

# Expected:
# - 0x27: Display 1 (20x4 LCD)
# - 0x20: Arcade buttons (eller annan adress om 0x20 är upptagen)
# OBS: Om 0x20 redan används, konfigurera arcade buttons på annan adress
```

### Testa Mode Latch Logic
1. Starta system i Auto-läge (standard)
2. Tryck I06 (Manual) → Verifiera MW60=0
3. Tryck I05 (Auto) → Verifiera MW60=1
4. Verifiera att tillstånd bibehålls efter knappslitning

### Testa Motor Protection
1. **VARNING:** Testa endast med säker setup, pump frånkopplad
2. Simulera I10 hög signal
3. Verifiera omedelbar pumpstop
4. Verifiera BlockReason=7, EventMask bit 5
5. Verifiera att reset inte fungerar medan I10 är hög
6. Rensa I10, tryck reset → Verifiera återställning

## Migreringsguide från V1

### Ändrade Digital Inputs
| Gammal | Ny | Ändring |
|--------|-----|---------|
| DI3 (Switch_Auto) | I05 (Button_Set_Auto) | 1-0-2 switch → Pulse button med latch |
| DI10 (Switch_Manual) | I06 (Button_Set_Manual) | 1-0-2 switch → Pulse button med latch |
| DI8 (E_Stop) | I03 (E_Stop) | Pin-förskjutning |
| - | I08 (Soft_Starter_Fault) | NY - mjukstartare fault |
| - | I10 (Motor_Protection) | NY - motorskydd Q1 |

### Borttagna Komponenter
- **Display 2 (D2):** Ersatt av Display 1 + Arcade buttons
- **Menu Buttons (DI11-DI14):** Flyttade till I2C arcade buttons
- **MW64 (MenuButtonsReg):** DEPRECATED, används ej längre

### Nya Komponenter
- **I2C Arcade Buttons:** 4 st knappar för menynavigering
- **Analog A2:** Jordtemperatursensor
- **MW37:** Jordtemperatur råvärde

## Support och Felsökning

### Kontakta
- **GitHub Issues:** https://github.com/erikohliv/fotbollsplan-bevattning/issues
- **Wiki:** Se repository wiki för mer dokumentation

### Vanliga Problem

**Problem:** Auto/Manual-läge växlar inte  
**Lösning:** Kontrollera I05/I06 anslutningar, verifiera edge-detection i PLC

**Problem:** Motorskydd larm fastnar  
**Lösning:** Kontrollera fysisk motorskydd Q1, verifiera I10 signal går låg, tryck reset

**Problem:** Arcade buttons svarar inte  
**Lösning:** Kontrollera I2C-adress med `i2cdetect`, verifiera anslutningar

**Problem:** Display 1 visar fel data  
**Lösning:** Kontrollera Modbus-anslutning (MW70 heartbeat), verifiera PLC körning
