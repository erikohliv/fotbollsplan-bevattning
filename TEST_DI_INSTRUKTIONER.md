# TESTINSTRUKTIONER - Digitala Ingångar (DI1-DI12)

## 🎯 Syfte
Verifiera att varje digital ingång kan läsas korrekt via Modbus.

---

## 🔧 Förberedelse

### 1. Starta DI-monitorn
```bash
cd ~/fotbollsplan-bevattning
source .venv/bin/activate
python3 test_di_monitor.py
```

Monitorn visar **live-status** på alla DI. Den uppdateras automatiskt när du triggar en ingång.

---

## 📋 TEST-CHECKLISTA

### Typ av kontakter:
- **NC (Normally Closed):** Normalt sluten → HIGH (1) = OK, LOW (0) = Larm
- **NO (Normally Open):** Normalt öppen → LOW (0) = Inaktiv, HIGH (1) = Aktiverad

---

### ✅ DI1 - Lägesväljare AUTO (NC)
**GPIO:** 17  
**Förväntat:** HIGH (1) när omkopplare i AUTO-läge  
**Test:** 
1. Sätt omkopplare i AUTO → Ska visa HIGH (1)
2. Sätt omkopplare i annat läge → Ska visa LOW (0)

**Status:** ⬜ Testad

---

### ✅ DI2 - Lägesväljare FJÄRR (NC)
**GPIO:** 18  
**Förväntat:** HIGH (1) när omkopplare i FJÄRR-läge  
**Test:**
1. Sätt omkopplare i FJÄRR → Ska visa HIGH (1)
2. Sätt omkopplare i annat läge → Ska visa LOW (0)

**Status:** ⬜ Testad

---

### 🚨 DI3 - Nödstopp (NC) **KRITISK SÄKERHET**
**GPIO:** 27  
**Förväntat:** HIGH (1) = Nödstopp OK, LOW (0) = Nödstopp aktiverad  
**Test:**
1. Nödstopp ej tryckt → HIGH (1)
2. Tryck nödstopp → LOW (0)
3. Lossa nödstopp → HIGH (1) igen

**⚠️ VIKTIGT:** Om denna visar LOW (0) får systemet INTE starta pump!

**Status:** ⬜ Testad

---

### ✅ DI4 - Zonväljare Zon 1 (NO)
**GPIO:** 22  
**Förväntat:** LOW (0) = Ej vald, HIGH (1) = Vald  
**Test:**
1. Ingen zon vald → LOW (0)
2. Välj Zon 1 → HIGH (1)

**Status:** ⬜ Testad

---

### ✅ DI5 - Zonväljare Zon 2 (NO)
**GPIO:** 23  
**Förväntat:** LOW (0) = Ej vald, HIGH (1) = Vald  
**Test:**
1. Ingen zon vald → LOW (0)
2. Välj Zon 2 → HIGH (1)

**Status:** ⬜ Testad

---

### ✅ DI6 - Zonväljare Zon 3 (NO)
**GPIO:** 24  
**Förväntat:** LOW (0) = Ej vald, HIGH (1) = Vald  
**Test:**
1. Ingen zon vald → LOW (0)
2. Välj Zon 3 → HIGH (1)

**Status:** ⬜ Testad

---

### ✅ DI7 - Flödesvakt (NO)
**GPIO:** 25  
**Förväntat:** LOW (0) = Inget flöde, HIGH (1) = Flöde detekterat  
**Test:**
1. **Innan vatten:** Kortslut DI7 till GND → LOW (0)
2. **Innan vatten:** Koppla DI7 till 24VDC → HIGH (1)
3. **Med vatten:** Starta pump → Ska bli HIGH (1) när flöde kommer

**Status:** ⬜ Testad

---

### ✅ DI8 - Mjukstartare fel (NC)
**GPIO:** 5  
**Förväntat:** HIGH (1) = Mjukstartare OK, LOW (0) = Fel  
**Test:**
1. **Om du har mjukstartaren:** Anslut felkontakt
2. **Om inte:** Kortslut DI8 till 24VDC → HIGH (1), till GND → LOW (0)

**Status:** ⬜ Testad

---

### ✅ DI9 - Tryckvakt (NO)
**GPIO:** 8  
**Förväntat:** LOW (0) = Inget tryck, HIGH (1) = Tryck OK  
**Test:**
1. **Innan vatten:** Kortslut DI9 till GND → LOW (0)
2. **Innan vatten:** Koppla DI9 till 24VDC → HIGH (1)
3. **Med vatten:** Starta pump → Ska bli HIGH (1) vid tryck

**Status:** ⬜ Testad

---

### 🚨 DI10 - Motorskydd (NC) **KRITISK SÄKERHET**
**GPIO:** 11  
**Förväntat:** HIGH (1) = Motorskydd OK, LOW (0) = Motorskydd utlöst  
**Test:**
1. **Om du har motorskydd:** Anslut hjälpkontakt
2. **Om inte:** Kortslut DI10 till 24VDC → HIGH (1), till GND → LOW (0)

**⚠️ VIKTIGT:** Om denna visar LOW (0) ska pumpen stoppas omedelbart!

**Status:** ⬜ Testad

---

### 🚨 I11 - 24VDC säkring (NO) **KRITISK SÄKERHET**
**GPIO:** 9  
**Förväntat:** HIGH (1) = Säkring OK, LOW (0) = Säkring utlöst  
**Test:**
1. **Om du har säkring med hjälpkontakt:** Anslut
2. **Om inte:** Kortslut I11 till 24VDC → HIGH (1), till GND → LOW (0)

**⚠️ VIKTIGT:** Om denna visar LOW (0) får systemet INTE tillåta någon drift!

**Status:** ⬜ Testad

---

### ⚠️ I12 - 24VAC säkring (NO) **EJ ANSLUTEN**
**GPIO:** 10  
**Förväntat:** HIGH (1) = Säkring OK, LOW (0) = Säkring utlöst  
**Test:** **HOPPA ÖVER** - Du har inte komponenten ännu

**Status:** ⬜ Skippad (saknar hårdvara)

---

## 📊 Rapportering

### När du testat en ingång:
1. Skriv "TESTAD" i chatten
2. Ange vilken DI (t.ex. "DI3 testad, fungerar")
3. Ange HIGH/LOW status du såg

### Om något inte fungerar:
1. Skriv "DI3 fungerar INTE"
2. Beskriv vad som händer (fastnar på LOW, inget svar, etc.)

---

## 🎬 Exempel-session

```
Terminal 1:
$ python3 test_di_monitor.py

[Monitor visar alla DI som LOW]

Terminal 2 (du):
- Tryck nödstopp
[Monitor uppdateras → DI3 byter från LOW till LOW (eller HIGH→LOW om NC)]

- Lossa nödstopp
[Monitor uppdateras → DI3 byter tillbaka]

- Välj Zon 1
[Monitor uppdateras → DI4 byter från LOW till HIGH]
```

---

## 🚀 Kom igång!

Kör detta nu:
```bash
cd ~/fotbollsplan-bevattning
source .venv/bin/activate
python3 test_di_monitor.py
```

Sedan börjar du trigga ingångar och rapporterar vad du ser!
