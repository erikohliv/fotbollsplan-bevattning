# KRITISKT: UniPi Kernel-Moduler Saknas!

## 🔴 Problem Identifierat

### Vad vi hittade:
- **LED 3 på UniPi lyser** när DI3 triggas → Signalen når hårdvaran ✅
- **GPIO 27 läser LOW** i Raspberry Pi → GPIO fungerar inte ❌
- **`lsmod | grep unipi`** → Inga kernel-moduler laddade ❌

### Varför det inte fungerar:
UniPi 1.1 har en **egen mikroprocessor** som:
1. Tar emot 24V-signaler från plintbordet
2. Visar LED:erna (därför LED 3 lyser)
3. **MEN:** Raspberry Pi GPIO:erna måste konfigureras via **kernel-driver**

Utan kernel-driver:
- Raspberry Pi kan inte läsa GPIO:erna
- Alla DI läser alltid LOW
- Modbus-servern ser inga förändringar

## ✅ Lösning

### Installera UniPi kernel-moduler:
```bash
sudo su
wget -qO - https://repo.unipi.technology/debian/raspberry-unipi1.sh | bash
reboot
```

### Verifiera efter omstart:
```bash
# 1. Kolla att kernel-moduler är laddade
lsmod | grep unipi

# Ska visa något liknande:
# unipi_mfd
# unipi_gpio
# unipi_id

# 2. Kolla att enheter skapades
ls -l /dev/unipi*

# 3. Testa om GPIO fungerar nu
python3 << 'EOF'
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
print("DI3 (GPIO 27):", GPIO.input(27))
GPIO.cleanup()
EOF
```

### Sen kör vi DI-testet igen:
```bash
cd ~/fotbollsplan-bevattning
source .venv/bin/activate
python3 test_di_monitor.py
```

Nu ska det fungera! 🎉

---

## 📋 Vad som fungerar NU (utan kernel-moduler):

✅ Display 1 (LCD 20x4)  
✅ Modbus Server (port 502)  
✅ Reläer R1-R7 (via MCP23008 på I2C)  
✅ I2C-buss (alla enheter kommunicerar)  

❌ Digitala ingångar (DI1-DI12) - **KRÄVER kernel-moduler**  
⚠️ Analoga ingångar (AI1-AI2) - ADS1115 initialiseras inte

---

**Nästa steg:** Installera kernel-moduler → Reboot → Testa DI igen!

**Datum:** 2026-01-02  
**Status:** Väntar på kernel-modul-installation
