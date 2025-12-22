# Refaktorering: Analog till Digital Sensorer - Sammanfattning

## Översikt
Denna refaktorering ändrar tryckvakten och flödesvakten från analog till digital hårdvara, implementerar säkerhetslogik med timeout-övervakning, och tillhandahåller konfigurerbar polaritet för givare.

## Hårdvaruändringar

### Tryckvakt (Pressure Switch)
- **Tidigare**: Analog 0-10V givare på %IW1 (AI2), skalad till 0-100% i MW33
- **Nu**: Digital brytare på %IX0.4 (DI5), status 0/1 i MW33
- **Funktion**: Sluter vid tryck > X bar (t.ex. NO-givare sluter vid tryck)
- **Modbus-register**: MW33 - Pressure_Switch_Status (0=ingen tryck, 1=tryck OK)
- **Alarm-register**: MW54 - PressureAlarmReg (0=OK, 1=Timeout, 2=Oväntat tryck)

### Flödesvakt (Flow Switch)
- **Tidigare**: Digital ingång på %IX0.6 (DI7), fast polaritet
- **Nu**: Digital ingång på %IX0.6 (DI7), **konfigurerbar polaritet**
- **Funktion**: Sluter vid flöde (t.ex. NO-givare sluter vid flöde)
- **Modbus-register**: MW55 - FlowSwitchStatus (0=ingen flöde, 1=flöde OK)
- **Alarm-register**: MW56 - FlowAlarmReg (0=OK, 1=Initial timeout, 2=Torrkörning)

## PLC-ändringar (Fotbollsplan_Master_Version12.st)

### Borttagna komponenter
```structured-text
(* REMOVED *)
Analog_Pressure_Raw : INT; (* %IW1 - analog input *)
Pressure_Value : INT; (* MW33 - scaled 0-100% *)
```

### Nya komponenter
```structured-text
(* ADDED - Digital input *)
Switch_Pressure : BOOL; (* %IX0.4 - DI5 Tryckvakt *)

(* ADDED - Digital status *)
Pressure_Switch_Status : INT; (* MW33 - 0=ingen tryck, 1=tryck OK *)

(* ADDED - Alarm registers *)
PressureAlarmReg : INT; (* MW54 *)
FlowAlarmReg : INT; (* MW56 *)

(* ADDED - Configurable polarity *)
PRESSURE_OK_STATE : BOOL := TRUE;  (* TRUE=NO, FALSE=NC *)
FLOW_OK_STATE : BOOL := TRUE;      (* TRUE=NO, FALSE=NC *)

(* ADDED - Safety monitoring *)
PRESSURE_TIMEOUT_SEC : INT := 10;  (* Sekunder att vänta på tryck *)
FLOW_TIMEOUT_SEC : INT := 3;       (* Sekunder utan flöde innan larm *)
```

### Säkerhetslogik

#### Tryckövervaking
```structured-text
(* Vid pumpstart *)
IF Signal_Pump AND NOT Prev_Pump_State THEN
  Tmr_PressureTimeout(IN := TRUE, PT := T#1s * PRESSURE_TIMEOUT_SEC);
END_IF;

(* Under drift *)
IF Signal_Pump THEN
  IF Pressure_Switch_Status = 0 THEN
    IF Tmr_PressureTimeout.Q THEN
      PressureAlarm := 1;  (* Timeout *)
      Signal_Pump := FALSE;  (* STOPP *)
      BlockReason := 5;
    END_IF;
  END_IF;
ELSE
  (* Pump av - kontrollera oväntat tryck *)
  IF Pressure_Switch_Status = 1 THEN
    PressureAlarm := 2;  (* Oväntat tryck *)
  END_IF;
END_IF;
```

#### Flödesövervaking
```structured-text
(* Under drift *)
IF Signal_Pump THEN
  IF FlowSwitchStatus = 0 THEN
    Tmr_FlowTimeout(IN := TRUE, PT := T#1s * FLOW_TIMEOUT_SEC);
    IF Tmr_FlowTimeout.Q THEN
      FlowAlarm := 2;  (* Torrkörning *)
      Signal_Pump := FALSE;  (* STOPP *)
      BlockReason := 6;
    END_IF;
  ELSE
    (* Flöde OK - nollställ *)
    Tmr_FlowTimeout(IN := FALSE);
    FlowAlarm := 0;
  END_IF;
END_IF;
```

## Python API-ändringar (api_main.py)

### Borttagna konstanter
```python
# REMOVED
MW_PRESSURE = 33  # Analog 0-100%
PRESSURE_LOW_THRESHOLD = 20
PRESSURE_HIGH_THRESHOLD = 90
```

### Nya konstanter
```python
# ADDED
MW_PRESSURE_SWITCH = 33     # Digital 0/1
MW_PRESSURE_ALARM = 54      # Alarm kod
MW_FLOW_ALARM = 56          # Alarm kod

# Sensor polarity configuration
PRESSURE_OK_STATE = True    # Matchar PLC
FLOW_OK_STATE = True        # Matchar PLC
```

### Uppdaterad /status-endpoint
**Tidigare response**:
```json
{
  "pressure": 50,
  "flow_ok": true,
  "safety": {
    "slangbrott": false,
    "torrkorning": false,
    "givarkontroll": false,
    "blockering": false
  }
}
```

**Ny response**:
```json
{
  "pressure_switch": 1,
  "pressure_alarm": 0,
  "flow_switch": 1,
  "flow_alarm": 0,
  "safety": {
    "tryck_timeout": false,
    "oväntat_tryck": false,
    "torrkorning": false,
    "flöde_timeout": false,
    "tryck_ok": true,
    "flöde_ok": true
  }
}
```

## Modbus-registermappning

| Register | Namn (tidigare) | Namn (nu) | Typ | Beskrivning |
|----------|----------------|-----------|-----|-------------|
| MW33 | Pressure_Value (0-100%) | Pressure_Switch_Status (0/1) | Digital | Tryckvakt status |
| MW54 | - | PressureAlarmReg | Alarm | 0=OK, 1=Timeout, 2=Oväntat |
| MW55 | FlowSwitchStatus | FlowSwitchStatus | Digital | Flödesvakt status (oförändrat) |
| MW56 | - | FlowAlarmReg | Alarm | 0=OK, 1=Timeout, 2=Torrkörning |
| MW73 | BlockReasonReg | BlockReasonReg | Status | +5=Tryckfel, +6=Flödesfel |

### BlockReason-koder
```
0 = OK
1 = Regen > threshold
2 = Moisture > threshold
3 = Anti-kollision
4 = E-stop
5 = Tryckfel (NYTT)
6 = Flödesfel (NYTT)
```

## Konfiguration av givare

### Ändra polaritet i PLC
Redigera `Fotbollsplan_Master_Version12.st`:
```structured-text
(* NO-givare (Normally Open) - sluter vid aktivitet *)
PRESSURE_OK_STATE : BOOL := TRUE;
FLOW_OK_STATE : BOOL := TRUE;

(* NC-givare (Normally Closed) - bryter vid aktivitet *)
PRESSURE_OK_STATE : BOOL := FALSE;
FLOW_OK_STATE : BOOL := FALSE;
```

### Ändra timeout-värden
```structured-text
PRESSURE_TIMEOUT_SEC : INT := 10;  (* Default: 10 sekunder *)
FLOW_TIMEOUT_SEC : INT := 3;       (* Default: 3 sekunder *)
```

### Verifiering
1. Stoppa pumpen
2. Läs MW33: Ska vara 0 (ingen tryck)
3. Läs MW55: Ska vara 0 (inget flöde)
4. Om felaktigt, invertera polaritet i PLC

## Test och validering

### Testfall som verifierats
```python
# Normal drift
pressure_alarm=0, flow_alarm=0, pressure_ok=1, flow_ok=1, pump_on=1
→ Alla alarm=False

# Tryck-timeout efter pumpstart
pressure_alarm=1, flow_alarm=0, pressure_ok=0, flow_ok=1, pump_on=1
→ tryck_timeout=True

# Oväntat tryck när pump av
pressure_alarm=2, flow_alarm=0, pressure_ok=1, flow_ok=0, pump_on=0
→ oväntat_tryck=True

# Torrkörning (flöde förlorat)
pressure_alarm=0, flow_alarm=2, pressure_ok=1, flow_ok=0, pump_on=1
→ torrkorning=True

# Flöde initial timeout
pressure_alarm=0, flow_alarm=1, pressure_ok=1, flow_ok=0, pump_on=1
→ flöde_timeout=True
```

Alla tester: ✅ PASS

## Filer som ändrats

1. **Fotbollsplan_Master_Version12.st** - PLC-program med säkerhetslogik
2. **api_main.py** - FastAPI backend med uppdaterade endpoints
3. **display_manager.py** - Display manager med uppdaterad registermappning
4. **test_api_main.py** - Tester för digital sensorlogik
5. **README.md** - Dokumentation av nya register och säkerhetsfunktioner
6. **SENSOR_REFACTOR_SUMMARY.md** (denna fil) - Refaktoreringsammanfattning

## Migration och deployment

### Före deployment
1. Bekräfta att givarna är korrekt kopplade (DI5 för tryck, DI7 för flöde)
2. Verifiera polaritet (NO/NC) i hardware_map.csv
3. Uppdatera PLC-konstanter om polaritet är NC

### Deployment-steg
1. Ladda upp ny PLC-kod till UNIPI
2. Starta om API-servern: `sudo systemctl restart bevattning-api`
3. Testa manuell start med zon 1 via display
4. Verifiera MW54 och MW56 är 0 (inga alarm)
5. Övervaka första automatiska körning

### Rollback-plan
Om problem uppstår:
1. Ladda tillbaka föregående PLC-version
2. Återställ api_main.py från git (före denna refaktorering)
3. Starta om tjänster

## Fördelar med refaktoreringen

### Säkerhet
- ✅ Automatisk pumpstop vid tryckfel (förhindrar läckage)
- ✅ Automatisk pumpstop vid torrkörning (förhindrar pumpskada)
- ✅ Övervakat timeout på båda givarna
- ✅ Alarm-register för diagnostik

### Flexibilitet
- ✅ Konfigurerbar polaritet (NO/NC) i PLC
- ✅ Justerbara timeout-värden
- ✅ Enkel verifiering via Modbus-register

### Drift
- ✅ Tydliga felmeddelanden via BlockReason
- ✅ Reset-funktion för återställning (MW82)
- ✅ Detaljerad status via API

### Kostnadsbesparingar
- ✅ Billigare digitala brytare istället för analog givare
- ✅ Enklare installation (ingen analog kalibrering)
- ✅ Färre kablar och komponenter

## Support och felsökning

### Vanliga problem

#### Problem: MW33 visar alltid 0
**Lösning**: Kontrollera att tryckvakten är ansluten till DI5 (%IX0.4) och att polariteten är korrekt.

#### Problem: MW54 = 1 (Timeout) vid pumpstart
**Lösning**: 
1. Öka PRESSURE_TIMEOUT_SEC om pumpen behöver mer än 10s för att bygga tryck
2. Kontrollera tryckvaktens tröskelvärde (bar-inställning)
3. Verifiera att givaren sluter vid rätt tryck

#### Problem: MW56 = 2 (Torrkörning) trots flöde
**Lösning**:
1. Kontrollera att flödesvakten är ansluten till DI7 (%IX0.6)
2. Verifiera polaritet: Om NC-givare, sätt FLOW_OK_STATE := FALSE
3. Kontrollera flödesvaktens känslighet/inställning

#### Problem: MW54 = 2 (Oväntat tryck) när pump är av
**Lösning**:
1. Detta kan indikera läckage eller backventilfel
2. Kontrollera manuella ventiler (är de helt stängda?)
3. Verifiera backventil på utgången

### Diagnostik via API
```bash
# Hämta fullständig status
curl -H "X-API-Key: <nyckel>" http://<ip>:8000/status

# Kontrollera alarm
curl -H "X-API-Key: <nyckel>" http://<ip>:8000/menu/felsökning

# Reset fel
curl -X POST -H "X-API-Key: <nyckel>" http://<ip>:8000/menu/reset-error
```

## Kontaktinformation
Vid frågor eller problem med denna refaktorering, kontakta:
- **Projekt**: fotbollsplan-bevattning
- **Repository**: https://github.com/erikohliv/fotbollsplan-bevattning
- **Issue tracker**: https://github.com/erikohliv/fotbollsplan-bevattning/issues

---
*Dokumentet uppdaterat: 2025-12-22*
*Version: 1.0*
