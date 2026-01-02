# SYSTEMCHECKOUT - Fotbollsplan Bevattning System 2.0
**Datum:** 2026-01-02  
**Status:** Grundsystem verifierat utan full hårdvara

---

## ✅ FUNGERANDE KOMPONENTER

### 1. Display 1 (LCD 20x4) - I2C 0x27
- **Status:** ✅ FUNGERAR
- **Initialisering:** OK med nya robusta timings (2s startup delay + retry-logik)
- **Autorotation:** Fungerar (5 olika vyer)
- **Bakgrundsbelysning:** Aktiv
- **Test:** Efter boot visas text tydligt, ingen kontrast-justering behövdes

### 2. Modbus TCP Server (UniPi Emulation)
- **Status:** ✅ FUNGERAR
- **Port:** 502
- **Digitala ingångar:** 12 st (DI1-DI12) läsbara
- **Analoga ingångar:** 2 st (AI1-AI2, ADS1115 ej initialiserad men register finns)
- **Reläer (Coils):** 8 st (R1-R8) via MCP23008
- **Test:** Alla Modbus-läsningar/skrivningar fungerar korrekt

### 3. Reläer (MCP23008 via I2C)
- **Status:** ✅ FUNGERAR
- **Testad:** R1 (Pump), R2 (Zon 1), R3 (Zon 2), R4 (Zon 3)
- **Resultat:** Alla reläer aktiveras/avaktiveras via Modbus utan fel
- **Klickljud:** Ska höras från varje relä när det aktiveras
- **Säkerhet:** Testa gjordes UTAN vatten i systemet

### 4. Arkadknappar (PCF8574)
- **Status:** ⚠️ DELVIS FUNGERAR
- **I2C-adress:** 0x20 (fungerande), 0x21 (ej funnen)
- **Problem:** Alla knappar läser som "tryckt" (0x00), troligen:
  - Knappar ej inkopplade
  - Saknar pull-up resistorer
  - Fel polaritet
- **Åtgärd:** Kontrollera hårdvarukoppling (behöver NO-knappar med pull-ups)

### 5. Python Services (systemd)
- **display-manager:** ✅ Körs och visar data
- **unipi-modbus:** ✅ Körs och svarar på Modbus-anrop
- **bevattning-controller:** ⚠️ Ej testad (väntar på fler ingångar)
- **bevattning-api:** ⚠️ Ej testad

### 6. I2C-buss
- **Status:** ✅ FUNGERAR
- **Detekterade enheter:**
  - `0x20` - Arkadknappar (PCF8574)
  - `0x27` - Display 1 (LCD 20x4)
  - `0x68` - ADS1115 (ADC för analoga ingångar)
  - Övriga - UniPi komponenter

---

## ⚠️ EJ TESTADE/VÄNTANDE KOMPONENTER

### 1. Digitala Ingångar (DI1-DI12) - **KRÄVER KERNEL-MODULER**
- **Status:** Alla läser LOW (0) - FÖRVÄNTAT utan kernel-moduler
- **Problem upptäckt:** 
  - **LED 3 lyser** när DI3 triggas = Signalen når hårdvaran ✅
  - **GPIO 27 läser LOW** = Raspberry Pi GPIO fungerar inte ❌
  - **Orsak:** **UniPi kernel-moduler SAKNAS**
  
- **Lösning:** Installera UniPi kernel-moduler
  ```bash
  # För UniPi 1.1 på Raspberry Pi OS
  sudo su
  wget -qO - https://repo.unipi.technology/debian/raspberry-unipi1.sh | bash
  reboot
  ```

- **Varför behövs kernel-moduler:**
  - UniPi 1.1 har egen mikroprocessor som läser 24V-signaler
  - LED:erna visar att mikroprocessorn ser signalerna
  - Men Raspberry Pi GPIO måste konfigureras av kernel-driver
  - Utan driver: GPIO läser alltid LOW trots att LED lyser

- **Efter installation:**
  - Kernel-moduler skapar `/dev/unipi*`-enheter
  - GPIO:erna mappas korrekt via device tree
  - Modbus-servern kan då läsa DI via GPIO.input()

- **Nästa steg:** Anslut följande när kernel-moduler är installerade:
  - **DI1:** Lägesväljare AUTO (NC-kontakt)
  - **DI2:** Lägesväljare FJÄRR (NC-kontakt)
  - **DI3:** Nödstopp (NC-kontakt, KRITISK!)
  - **DI7:** Flödesvakt (NO-kontakt)
  - **DI8:** Mjukstartare fel (NC-kontakt)
  - **DI9:** Tryckvakt (NO-kontakt)
  - **DI10:** Motorskydd (NC-kontakt)
  - **DI11:** 24VDC säkring hjälpkontakt (NO)
  - **I12:** 24VAC säkring hjälpkontakt (NO) - **EJ ANSLUTEN ÄNNU**

### 2. Analoga Ingångar (AI1-AI2)
- **Status:** Läser 0 (raw)
- **Problem:** ADS1115 initialiseras inte korrekt i `unipi_modbus_server.py`
- **Log:** `WARNING - ✗ ADC kunde inte initialiseras, läs med alternativ metod`
- **Nästa steg:** 
  - Felsök ADS1115-kommunikation (I2C 0x68)
  - Verifiera att markfuktsensor och jordtempsensor kan anslutas

### 3. Säkerhetslogik
- **Status:** ⚠️ EJ TESTAD
- **Orsak:** Behöver DI3 (Nödstopp), DI10 (Motorskydd), I11, I12 anslutna
- **Kritiskt:** Systemet får INTE tillåta bevattning om:
  - Nödstopp är aktiverad (DI3=LOW)
  - Motorskydd utlöst (DI10=LOW)
  - 24VDC säkring utlöst (I11=LOW)
  - 24VAC säkring utlöst (I12=LOW) - **BYPASS AKTIV JUST NU**

### 4. Anti-Vattenslag-logik
- **Status:** ⚠️ EJ TESTAD
- **Logik:** Öppna ventil → Vänta 5s → Starta pump
- **Test:** Ska köras när vatten är anslutet

---

## 🔧 ÅTGÄRDSLISTA - Nästa steg

### Prioritet 0 - KERNEL-MODULER (KRITISKT)
**Utan dessa fungerar INGA digitala ingångar!**

```bash
# Installera UniPi kernel-moduler
sudo su
wget -qO - https://repo.unipi.technology/debian/raspberry-unipi1.sh | bash
reboot
```

**Verifiera efter reboot:**
```bash
lsmod | grep unipi  # Ska visa kernel-moduler
ls /dev/unipi*      # Ska visa enheter
```

### Prioritet 1 - SÄKERHET (efter kernel-moduler)
1. **Anslut Nödstopp (DI3)**
   - NC-kontakt till GPIO 27 (DI3)
   - Test: Tryck nödstopp → DI3=LOW → System blockerar

2. **Anslut Motorskydd (DI10)**
   - NC-kontakt till GPIO 11 (DI10)
   - Test: Simulera fel → DI10=LOW → Pump stoppas

3. **Anslut 24VDC säkring (I11)**
   - NO hjälpkontakt till GPIO 9 (I11)
   - Test: Bryt säkring → I11=LOW → System blockerar

4. **Installera 24VAC säkring (I12) - SAKNAS**
   - NO hjälpkontakt till GPIO 10 (I12)
   - När installerad: Ta bort bypass i `bevattning_controller.py`

### Prioritet 2 - DRIFT
5. **Anslut Lägesväljare**
   - DI1 (AUTO) + DI2 (FJÄRR) → GPIO 17, 18
   - Test: Växla mellan lägen

6. **Anslut Flödesvakt (DI7) & Tryckvakt (DI9)**
   - NO-kontakter till GPIO 25, 8
   - Test: Simulera fel → Pump stoppas

7. **Felsök ADS1115 (Analoga ingångar)**
   - Kontrollera I2C-kommunikation (0x68)
   - Aktivera AI1 (Markfukt) + AI2 (Jordtemp)

8. **Fixa Arkadknappar**
   - Kontrollera koppling på PCF8574 (0x20)
   - Lägg till pull-up resistorer om nödvändigt
   - Test: Varje knapp ska läsa korrekt ON/OFF

### Prioritet 3 - VATTENTEST
9. **Anslut vatten till systemet**
   - Ventiler (Zon 1-3)
   - Pump via mjukstartare
   - Flödesvakt + Tryckvakt

10. **Test med vatten (FÖRSIKTIG!)**
    - Starta Zon 1 → Öppna V1 → Vänta 5s → Starta pump
    - Verifiera flöde (DI7)
    - Verifiera tryck (DI9)
    - Stoppa pump → Stäng ventil

---

## 📊 SAMMANFATTNING

| Komponent | Status | Test | Notering |
|-----------|--------|------|----------|
| Display 1 (20x4) | ✅ OK | Visar text tydligt | Robusta init-timings |
| Modbus Server | ✅ OK | Svarar på port 502 | UniPi emulation |
| Reläer R1-R4 | ✅ OK | Aktiveras/avaktiveras | Lyssna efter klick |
| Arkadknappar | ⚠️ DELVIS | Läses som 0x00 | Fixa koppling/pull-ups |
| DI1-DI12 | ⚠️ VÄNTAR | Alla LOW | Ingen hårdvara ansluten |
| AI1-AI2 (ADS1115) | ❌ FEL | Läser 0 | ADC ej initialiserad |
| I12 (24VAC säkring) | ⚠️ BYPASS | - | Ej ansluten, bypass aktiv |
| Säkerhetslogik | ⚠️ VÄNTAR | - | Kräver DI3, DI10, I11, I12 |

---

## 🎯 NÄSTA MÖTE/TEST

1. **Anslut kritiska säkerhetskomponenter (DI3, DI10, I11)**
2. **Testa att Nödstopp blockerar systemet**
3. **Felsök ADS1115 för analoga ingångar**
4. **Planera vattentest (när säkerhet OK)**

---

**Uppdaterad:** 2026-01-02 16:55  
**Systemversion:** 2.0  
**Hardware:** Raspberry Pi 4 + UniPi 1.1 (emulerat)
