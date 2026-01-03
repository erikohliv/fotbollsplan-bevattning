# Schneider Electric Altistart ATS01N2 - Mjukstartare

**Modell:** Altistart ATS01N2  
**Tillverkare:** Schneider Electric  
**Funktion:** Soft starter för pump (mjuk uppstart och nedkörning)  
**Manual:** ATS01_IS_ATS01N2_1624686_05.pdf

---

## 📋 ÖVERSIKT

Mjukstartaren rampar mjukt upp pumpmotorn för att:
- Minska elektrisk startström (undvika säkringsutlösning)
- Minska mekanisk belastning på pump och rörsystem
- Undvika tryckstötar i vatten-systemet
- Förlänga livslängd på pump och elektrisk utrustning

---

## 🔌 ANSLUTNING

### Effektkrets
```
L1, L2, L3 (In)  → Nätspänning (3-fas 380-480V)
T1, T2, T3 (Out) → Till pump-motor
```

### Styrsignaler
```
LI+ / LI1 / LI2  → Startsignal från PLC (Relä 8)
COM              → Common (0V referens)
```

### Fault Relay (R1)
```
R1A - R1C  → Växlande reläkontakt
           → Kopplad till DI8 (Soft_Starter_Fault)
```

**Normalt (OK):**
- R1A-R1C är **SLUTEN**
- NO-kontakt aktiverad
- DI8 dras till jord → men inverterad i kod → HIGH i Modbus

**Vid fel:**
- R1A-R1C **ÖPPNAS**
- Relä faller av
- DI8 öppen → pull-up drar upp → men inverterad → LOW i Modbus
- PLC läser LOW → Stoppar pump → BlockReason=8

---

## ⚠️ FEL SOM MJUKSTARTAREN UPPTÄCKER

### 1. Termiskt Skydd (Överhettning)
- Mjukstartaren blir för varm
- Auto-reset när svalnat

### 2. Överström
- Motorström för hög (överbelastning)
- Indikerar pumpproblem eller mekanisk blockering

### 3. Fasförlust
- En eller flera faser saknas
- Kritiskt - kan skada motor

### 4. Asymmetri
- Obalanserade faser
- Kan indikera elektriskt problem

### 5. Underström
- Motor drar för lite ström
- Kan betyda att motor inte är kopplad

### 6. Överströmstid
- Motorn tar för lång tid att starta
- Kan betyda tung start eller mekaniskt problem

### 7. Intern Elektronik-fel
- Problem i mjukstartarens styrelektronik
- Kräver service/byte

---

## 🔧 SYSTEMINTEGRATION

### PLC-koppling (DI8)
```
Altistart R1A-R1C → UNIPI DI8 (I08)
                 → %IX0.7 i PLC
                 → Modbus Discrete Input 7
```

### PLC-reaktion vid fel:
```c
1. DI8 läser LOW (fel detekterat)
2. Signal_Pump = FALSE (pump stoppas)
3. BlockReason = 8 (Mjukstartare fel)
4. Systemet blockeras
```

### Auto-reset:
```c
När DI8 går HIGH igen (fel åtgärdat):
  → Soft_Starter_Fault_Active = FALSE
  → BlockReason = 0 (rensat)
  → Systemet kan köras igen
```

**Ingen manuell reset behövs på PLC-sidan!**

---

## 📊 STATUS I WEBBGRÄNSSNITT

### DI Monitor (Port 8081)
```
DI8 (Mjukstartare Fault):
  HIGH/TRUE  = ✅ OK (grön)
  LOW/FALSE  = 🔴 LARM (röd, men EJ kritisk - orange)
```

### Dashboard Hub / Bevattning API
Vid mjukstartare-fel:
- BlockReason visas som "Mjukstartare fel"
- Pump stoppad
- Auto-reset när fel försvinner

---

## 🔍 FELSÖKNING

### Problem: Mjukstartare larmar kontinuerligt

**Möjliga orsaker:**
1. Motor överbelastad
2. Mekaniskt problem i pump
3. Fel fasning (L1/L2/L3)
4. För lång starttid (justera parametrar)
5. Mjukstartare defekt

**Åtgärder:**
1. Kontrollera motor-strömuttag
2. Lyssna på pump vid start (konstiga ljud?)
3. Kontrollera fasföljd
4. Kontrollera att pumpen kan rotera fritt
5. Läs mjukstartar-display (om sådan finns)

### Problem: Pump startar inte

**Kontrollera:**
1. Är R8 (Pump_Enable) aktiverad? (Se DI Monitor eller Bevattning API)
2. Har mjukstartaren spänning?
3. Är LI+ / LI1 anslutet korrekt?
4. DI8 status i DI Monitor?

---

## 📖 DOKUMENTATION

- **Manual:** `documentation/ATS01_IS_ATS01N2_1624686_05.pdf`
- **Schneider Electric:** https://www.schneider-electric.com
- **Produkt:** Altistart 01 (ATS01)

---

## ⚙️ PARAMETRAR (Om justerbar)

Om din mjukstartare har parametrar som kan justeras:

**Starttid (Ramp-up):**
- Rekommenderat: 10-20 sekunder
- För snabb → hård start, ström-stöt
- För långsam → övertemperatur

**Stopptid (Ramp-down):**
- Rekommenderat: 5-10 sekunder
- Mjuk avstängning för att undvika vattenslag

**Överströmsskydd:**
- Justera efter motor-märkström
- Typiskt 300-400% av märkström

---

**Systemet är konfigurerat korrekt för din Altistart ATS01N2!** ✅

