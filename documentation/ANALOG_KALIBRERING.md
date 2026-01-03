# Kalibrering av Analoga Enheter

## 📊 Översikt

Systemet har två analoga ingångar via ADS1115 ADC (I2C-adress `0x68`):

- **AI1:** Markfuktgivare (0-10V → 0-100%)
- **AI2:** Jordtemperatur (0-10V → temperatur i °C)

---

## 🔧 Hårdvaruöversikt

### ADS1115 ADC
- **I2C-adress:** `0x68`
- **Upplösning:** 16-bit
- **Gain:** 1 (±4.096V range)
- **Spänningsdelare:** UniPi 1.1 har inbyggd delare: 0-10V → 0-3.3V

### Nuvarande Skalning
I `unipi_modbus_server.py`:
```python
# Läser voltage från ADS1115 (0-3.3V efter spänningsdelare)
voltage = self.ai1.voltage  # eller self.ai2.voltage

# Skalar till Modbus-värde (0-10000 motsvarar 0-10V)
scaled_value = int((voltage / 3.3) * 10000)
```

**Modbus-register:**
- **AI1 (Markfukt):** Input Register 0 → 0-10000 (0-10V)
- **AI2 (Temperatur):** Input Register 1 → 0-10000 (0-10V)

---

## 📋 Kalibreringsprocedur

### Steg 1: Verifiera Hårdvaruanslutning

1. **Kontrollera I2C-kommunikation:**
   ```bash
   i2cdetect -y 1
   ```
   Ska visa `0x68` (ADS1115)

2. **Kontrollera att 24V är på:**
   - Sensorerna behöver strömförsörjning
   - Verifiera att 24VDC-säkringen (DI11) är OK

3. **Kontrollera kopplingar:**
   - AI1: Markfuktgivare (0-10V)
   - AI2: Jordtemperaturgivare (0-10V)
   - GND: Gemensam jord
   - +24V: Strömförsörjning (om sensorer kräver det)

---

### Steg 2: Testa med Känd Spänning (Verifiering)

**För att verifiera att skalningen stämmer:**

1. **Anslut variabel spänningskälla (0-10V) till AI1 eller AI2**

2. **Läs Modbus-värden:**
   ```bash
   # Via Python
   python3 << 'EOF'
   from pymodbus.client import ModbusTcpClient
   
   client = ModbusTcpClient('127.0.0.1', port=502)
   client.connect()
   
   # Läs AI1 (Input Register 0)
   rr1 = client.read_input_registers(0, 1, device_id=1)
   ai1_value = rr1.registers[0] if not rr1.isError() else 0
   voltage1 = (ai1_value / 10000) * 10
   
   # Läs AI2 (Input Register 1)
   rr2 = client.read_input_registers(1, 1, device_id=1)
   ai2_value = rr2.registers[0] if not rr2.isError() else 0
   voltage2 = (ai2_value / 10000) * 10
   
   print(f"AI1 (Markfukt): Modbus={ai1_value}, Voltage={voltage1:.2f}V")
   print(f"AI2 (Temperatur): Modbus={ai2_value}, Voltage={voltage2:.2f}V")
   
   client.close()
   EOF
   ```

3. **Testpunkter:**
   | Spänning | Förväntat Modbus | Tolerans |
   |----------|-------------------|----------|
   | 0V       | ~0                | ±100     |
   | 5V       | ~5000             | ±200     |
   | 10V      | ~10000            | ±200     |

4. **Om värdena avviker:**
   - Kontrollera spänningsdelare (ska vara 0-10V → 0-3.3V)
   - Justera skalning i `unipi_modbus_server.py` om nödvändigt

---

### Steg 3: Kalibrera Markfuktgivare (AI1)

**Mål:** 0V = 0% fukt, 10V = 100% fukt

1. **Fysisk kalibrering:**
   - **Torr mark (0%):** Verifiera att sensorn ger ~0V
   - **Mättad mark (100%):** Verifiera att sensorn ger ~10V
   - Om sensorn har kalibreringspotentiometer, justera vid dessa punkter

2. **Verifiera via webbgränssnitt:**
   - Gå till **Bevattning API** (port 8000)
   - Klicka på **"Sensor Status"**
   - Kontrollera att markfukt visas korrekt (0-100%)

3. **Om skalningen behöver justeras:**
   - Redigera `unipi_modbus_server.py`, funktion `read_analog_input()`
   - Justera formeln om sensorn har annat spänningsområde

---

### Steg 4: Kalibrera Jordtemperaturgivare (AI2)

**Mål:** Konvertera 0-10V till temperatur i °C

**Typiska temperatursensorer:**
- **PT100/PT1000:** Ofta 0-10V motsvarar -50°C till +150°C
- **Andra sensorer:** Kolla sensorns datablad

1. **Bestäm temperaturomfång:**
   - Kolla sensorns datablad
   - Exempel: 0V = -50°C, 10V = +150°C → 200°C spann

2. **Implementera omvandling:**
   
   **I PLC-koden (`Fotbollsplan_Master_Version12.st`):**
   ```st
   (* Läs råvärde från Modbus *)
   Analog_Temp_Raw := %IW1;  // 0-10000 (0-10V)
   
   (* Omvandla till voltage *)
   Analog_Temp_Voltage := (Analog_Temp_Raw / 10000.0) * 10.0;
   
   (* Omvandla till temperatur (exempel: 0V=-50°C, 10V=+150°C) *)
   Jordtemperatur := -50.0 + (Analog_Temp_Voltage * 20.0);  // 200°C / 10V = 20°C/V
   ```

3. **Fysisk kalibrering:**
   - **Känd temperatur:** Använd termometer för referens
   - **Jämför:** Verifiera att sensorns spänning stämmer
   - Justera formeln om nödvändigt

4. **Testa:**
   ```bash
   # Läs temperatur via API
   curl -H "X-API-Key: <din-nyckel>" http://localhost:8000/sensor-status
   ```

---

## 🛠️ Justering av Skalning

Om skalningen behöver justeras, redigera `unipi_modbus_server.py`:

```python
def read_analog_input(self, channel):
    """Läs analog ingång med anpassad skalning"""
    if not self.ads:
        return 0
    
    try:
        # Läs voltage från ADS1115
        if channel == 1:
            voltage = self.ai1.voltage  # 0-3.3V (efter spänningsdelare)
        elif channel == 2:
            voltage = self.ai2.voltage
        else:
            return 0
        
        # NUvarande skalning: 0-3.3V → 0-10000
        # Om du behöver justera, ändra multiplikatorn här:
        scaled_value = int((voltage / 3.3) * 10000)
        
        # Alternativ: Om spänningsdelaren är annorlunda
        # scaled_value = int((voltage / 3.3) * 10000 * correction_factor)
        
        return max(0, min(10000, scaled_value))
    except Exception as e:
        logger.error(f"✗ Kunde inte läsa analog ingång {channel}: {e}")
        return 0
```

---

## 📊 Verifiering via Webbgränssnitt

1. **Bevattning API (port 8000):**
   - Gå till `/sensor-status`
   - Kontrollera att markfukt och temperatur visas korrekt

2. **DI Monitor (port 8081):**
   - Visar inte analoga värden direkt, men kan användas för att verifiera att systemet fungerar

3. **Dashboard Hub (port 8090):**
   - Visar sensorstatus i översikten

---

## 🔍 Felsökning

### Problem: Värdena är alltid 0
- **Kontrollera:** Är ADS1115 ansluten? (`i2cdetect -y 1`)
- **Kontrollera:** Har sensorerna strömförsörjning?
- **Kontrollera:** Är kablarna korrekt anslutna?

### Problem: Värdena är felaktiga
- **Kontrollera:** Spänningsdelare (ska vara 0-10V → 0-3.3V)
- **Kontrollera:** Sensorernas spänningsområde (ska vara 0-10V)
- **Justera:** Skalningsformeln i `unipi_modbus_server.py`

### Problem: Värdena fluktuerar mycket
- **Kontrollera:** Kabelanslutningar (lösa kontakter?)
- **Kontrollera:** Jording (gemensam GND?)
- **Överväg:** Lägg till filtrering/medelvärdesberäkning i PLC-koden

---

## 📝 Checklista

- [ ] Verifiera I2C-kommunikation (`i2cdetect -y 1` visar `0x68`)
- [ ] Testa med känd spänning (0V, 5V, 10V)
- [ ] Verifiera Modbus-värden stämmer
- [ ] Kalibrera markfuktgivare (0% och 100% fukt)
- [ ] Kalibrera jordtemperaturgivare (känd temperatur)
- [ ] Verifiera via webbgränssnitt
- [ ] Dokumentera sensormodell och kalibreringsvärden

---

## 📚 Referenser

- **UNIPI_GPIO_MAPPING.md:** Hårdvarumappning
- **MARKFUKTGIVARE_REVIEW.md:** Markfuktgivare-specifikationer
- **unipi_modbus_server.py:** Implementering av analog läsning
- **Fotbollsplan_Master_Version12.st:** PLC-kod för omvandling

---

**Senast uppdaterad:** 2026-01-03

