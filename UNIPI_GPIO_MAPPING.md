# UniPi 1.1 GPIO och I2C-mappning

## Översikt

UniPi 1.1 använder en kombination av I2C-chips och Raspberry Pi GPIO-pinnar för sina I/O-funktioner.

---

## 🔌 I2C-enheter (Bus 1)

| Adress | Chip | Funktion | Pinnar |
|--------|------|----------|--------|
| **0x20** | MCP23008 | 8 Reläer | R1-R8 |
| **0x68** | ADS1115 | ADC | AI1-AI2 (Kanal 0-1) |
| **0x27** | PCF8574 | LCD Display 1 | 20x4 tecken |
| **0x20** | PCF8574 | Arkadknappar | 4 knappar (konfliktar EJ med MCP) |

---

## 🔄 Digitala Utgångar (Reläer R1-R8)

**Chip:** MCP23008 på I2C-adress `0x20`

| Relä | MCP Pin | Hardware_map | Funktion | Koppling |
|------|---------|--------------|----------|----------|
| R1 | Pin 7 | %QX0.0 | Valve_1 | Zone 1 ventil |
| R2 | Pin 6 | %QX0.1 | Valve_2 | Zone 2 ventil |
| R3 | Pin 5 | %QX0.2 | Valve_3 | Zone 3 ventil |
| R4 | Pin 4 | %QX0.3 | Valve_4 | Zone 4 ventil |
| R5 | Pin 3 | %QX0.4 | Valve_5 | Zone 5 ventil |
| R6 | Pin 2 | %QX0.5 | Valve_6 | Zone 6 ventil |
| R7 | Pin 1 | %QX0.6 | Valve_7 | Zone 7 ventil |
| R8 | Pin 0 | %QX0.7 | Pump_Enable | Pump via mjukstartare |

**Notering:** MCP23008-mappningen är omvänd (Pin 7 = R1, Pin 0 = R8)

---

## 📥 Digitala Ingångar (DI1-DI14)

**Metod:** Raspberry Pi GPIO (BCM-numrering)

| DI | GPIO BCM | Hardware_map | Variabel | Funktion | Typ |
|----|----------|--------------|----------|----------|-----|
| **DI1** | GPIO 4 | %IX0.0 | Button_Stop | Stoppknapp S202 | Momentary |
| **DI2** | GPIO 17 | %IX0.1 | Button_Start | Startknapp S201 | Momentary |
| **DI3** | GPIO 27 | %IX0.2 | E_Stop | Nödstopp S205 | Maintained |
| **DI4** | GPIO 23 | %IX0.3 | Button_Reset | Resetknapp S203 | Momentary |
| **DI5** | GPIO 22 | %IX0.4 | Button_Set_Auto | Auto-läge S204 | Pulse |
| **DI6** | GPIO 24 | %IX0.5 | Button_Set_Manual | Manuell-läge S204 | Pulse |
| **DI7** | GPIO 11 | %IX0.6 | Flow_Switch | Flödesvakt | Digital |
| **DI8** | GPIO 7 | %IX0.7 | Soft_Starter_Fault | Mjukstartare larm | Digital |
| **DI9** | GPIO 8 | %IX1.0 | Pressure_Switch | Tryckvakt | Digital |
| **DI10** | GPIO 9 | %IX1.1 | Motor_Protection | Motorskydd Q1 | Digital |
| **DI11** | GPIO 25 | %IX1.2 | Fuse_24VDC | Säkring PLC/Sensorer | NC-kontakt |
| **DI12** | GPIO 10 | %IX1.3 | Fuse_24VAC | Säkring Ventiler | NC-kontakt |
| DI13 | GPIO 5 | - | (Ej använd) | Kräver lödning |
| DI14 | GPIO 6 | - | (Ej använd) | Kräver lödning |

**Notering:** DI13 och DI14 är inte tillgängliga utan hårdvarumodifiering.

---

## 📊 Analoga Ingångar (AI1-AI2)

**Chip:** ADS1115 ADC på I2C-adress `0x68`

| Ingång | ADS Kanal | Hardware_map | Variabel | Funktion | Spänning |
|--------|-----------|--------------|----------|----------|----------|
| **AI1** | Channel 0 (P0) | %IW0 | Sensor_Moisture | Markfuktgivare | 0-10V |
| **AI2** | Channel 1 (P1) | %IW1 | Sensor_Temperature | Jordtemperatur | 0-10V |

**ADS1115 Specifikationer:**
- 16-bit upplösning
- Programmable Gain Amplifier (PGA)
- Standard gain=1 → ±4.096V range
- UniPi 1.1 har spänningsdelare: 0-10V → 0-3.3V

**Skalning i Modbus:**
- Modbus Input Register värde: 0-10000
- Motsvarar: 0-10V på fysisk ingång
- Formel: `voltage = (modbus_value / 10000) * 10`

---

## 📤 Analog Utgång (AO1)

**Metod:** Raspberry Pi PWM via GPIO 18

| Utgång | GPIO | Frekvens | Användning |
|--------|------|----------|------------|
| **AO1** | GPIO 18 | 100 Hz | (Ej implementerad i nuvarande system) |

---

## 🔗 Modbus TCP-mappning

Systemet exponerar UniPi:s I/O via Modbus TCP på port **502**:

### Coils (Function Code 01/05/15) - Read/Write
| Adress | Hårdvara | Beskrivning |
|--------|----------|-------------|
| 0 | R1 | Zone 1 ventil |
| 1 | R2 | Zone 2 ventil |
| 2 | R3 | Zone 3 ventil |
| 3 | R4 | Zone 4 ventil |
| 4 | R5 | Zone 5 ventil |
| 5 | R6 | Zone 6 ventil |
| 6 | R7 | Zone 7 ventil |
| 7 | R8 | Pump enable |

### Discrete Inputs (Function Code 02) - Read Only
| Adress | Hårdvara | Beskrivning |
|--------|----------|-------------|
| 0 | DI1 | Stoppknapp |
| 1 | DI2 | Startknapp |
| 2 | DI3 | Nödstopp |
| 3 | DI4 | Resetknapp |
| 4 | DI5 | Auto-läge |
| 5 | DI6 | Manuell-läge |
| 6 | DI7 | Flödesvakt |
| 7 | DI8 | Mjukstartare larm |
| 8 | DI9 | Tryckvakt |
| 9 | DI10 | Motorskydd |
| 10 | DI11 | Säkring 24VDC |
| 11 | DI12 | Säkring 24VAC |

### Input Registers (Function Code 04) - Read Only
| Adress | Hårdvara | Värde | Beskrivning |
|--------|----------|-------|-------------|
| 0 | AI1 | 0-10000 | Markfukt (0-10V) |
| 1 | AI2 | 0-10000 | Temperatur (0-10V) |

---

## 🔧 Konfiguration i unipi_modbus_server.py

```python
# I2C Bus
I2C_BUS = 1

# I2C-adresser
MCP23008_ADDRESS = 0x20  # Reläkontroller
ADS1115_ADDRESS = 0x68   # ADC

# GPIO BCM-pinnar (digitala ingångar)
DI_GPIO_PINS = [
    4,   # DI1
    17,  # DI2
    27,  # DI3
    23,  # DI4
    22,  # DI5
    24,  # DI6
    11,  # DI7
    7,   # DI8
    8,   # DI9
    9,   # DI10
    25,  # DI11
    10,  # DI12
]

# Modbus TCP
MODBUS_PORT = 502
```

---

## 🧪 Testning

### Testa I2C-enheter
```bash
i2cdetect -y 1
```

Förväntat resultat:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
20: 20 -- -- -- -- -- -- 27 -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
```

### Läs GPIO-status
```bash
# Visa GPIO-status
gpio readall

# Eller via Python
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(4, GPIO.IN); print('DI1:', GPIO.input(4))"
```

### Test via Modbus
```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('127.0.0.1', port=502)
client.connect()

# Läs digitala ingångar
di = client.read_discrete_inputs(0, 12, slave=1)
print("Digitala ingångar:", di.bits[:12])

# Läs analoga ingångar  
ai = client.read_input_registers(0, 2, slave=1)
print("AI1:", ai.registers[0], "AI2:", ai.registers[1])

# Sätt relä
client.write_coil(0, True, slave=1)  # R1 ON
```

---

## 📚 Referenser

- [UniPi 1.1 Knowledge Base](https://kb.unipi.technology/en:hw:01-unipi1.x:description-of-models-1-0)
- [Evok Configuration Guide](https://github.com/UniPi-technology/evok)
- [MCP23008 Datasheet](https://www.microchip.com/en-us/product/MCP23008)
- [ADS1115 Datasheet](https://www.ti.com/product/ADS1115)
- [RPi.GPIO Documentation](https://pypi.org/project/RPi.GPIO/)

---

## ⚠️ Viktiga Notiser

1. **GPIO-konflikt:** PCF8574 (knappar på 0x20) och MCP23008 (reläer på 0x20) delar adress men är på olika I2C-bussar eller har olika chip-select
2. **Pull-resistors:** GPIO-ingångar är konfigurerade med `pull_up_down=GPIO.PUD_DOWN`
3. **NC-kontakter:** DI11 och DI12 (säkringar) är Normally Closed - de är HIGH när säkringen är OK
4. **Spänningsnivåer:** Alla GPIO-ingångar är 3.3V logik (0V=LOW, 3.3V=HIGH)
5. **24V-isolering:** UniPi 1.1 har optoisolerade ingångar, 24V → 3.3V-omvandlare

---

*Senast uppdaterad: 2026-01-01*
