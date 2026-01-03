# Installation Verification Checklist

**Efter installation av Fotbollsplan Bevattning System 2.0**

## ✅ SNABB VERIFIERING

### 1. Kontrollera alla tjänster körs:

```bash
bash verify.sh
```

**Eller manuellt:**
```bash
systemctl status bevattning-api bevattning-controller display-manager \
  unipi-modbus dashboard-hub di-monitor user-management \
  todo-checklist dash-process-view
```

**Förväntat resultat:** Alla ska visa `active (running)`

---

### 2. Kontrollera I2C-enheter:

```bash
i2cdetect -y 1
```

**Förväntat resultat:**
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: 20 -- -- -- -- -- -- 27 -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
```

- `0x20` = MCP23008 (Reläer) ✅
- `0x27` = LCD Display ✅
- `0x68` = ADS1115 (ADC) ✅

---

### 3. Testa webbgränssnitt:

**Hitta IP-adress:**
```bash
hostname -I
```

**Testa Dashboard Hub (startsida):**
```bash
IP=$(hostname -I | awk '{print $1}')
curl -s http://$IP:8090 | grep -q "Dashboard Hub" && echo "✅ Dashboard Hub fungerar"
```

**Testa alla gränssnitt:**
```bash
IP=$(hostname -I | awk '{print $1}')
echo "Dashboard Hub:      http://$IP:8090"
echo "Bevattning API:     http://$IP:8000"
echo "DI Monitor:         http://$IP:8081"
echo "Användarhantering:  http://$IP:8082"
echo "Process View:       http://$IP:8050"
echo "TODO Checklist:     http://$IP:8080"
```

**Öppna Dashboard Hub i webbläsare och verifiera:**
- ✅ Snabbstatistik visas (Zon, Pump, Läge, Larm)
- ✅ Alla 5 tjänstekort visar "🟢 Online"
- ✅ Länkar fungerar

---

### 4. Testa API-nyckel:

```bash
API_KEY=$(grep API_KEY api_.env | cut -d= -f2 | tr -d '"')
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/status | python3 -m json.tool
```

**Förväntat resultat:** JSON-svar med systemstatus

---

### 5. Testa DI Monitor:

**Öppna i webbläsare:**
```
http://<ip>:8081
```

**Verifiera:**
- ✅ Alla 12 DI visas
- ✅ Uppdateras automatiskt
- ✅ Färgkodning fungerar

**Testa knapp:**
1. Tryck på en fysisk knapp (om tillgänglig)
2. Se att DI ändrar status direkt

---

### 6. Testa användarhantering:

**Öppna i webbläsare:**
```
http://<ip>:8082
```

**Logga in:**
- Användarnamn: `superadmin`
- Lösenord: (ditt superadmin-lösenord)

**Verifiera:**
- ✅ Inloggning fungerar
- ✅ Användarlista visas (tom eller med användare)
- ✅ Kan skapa testanvändare

---

## 🔧 FELSÖKNING

### Problem: Tjänst visar "inactive" eller "failed"

```bash
# Se detaljerad status
sudo systemctl status <tjänst-namn>

# Se loggar
journalctl -u <tjänst-namn> -n 50

# Starta om tjänst
sudo systemctl restart <tjänst-namn>
```

### Problem: Kan inte nå webbgränssnitt

**1. Kontrollera firewall (om aktiv):**
```bash
sudo ufw status
# Om aktiv, öppna portar:
sudo ufw allow 8000,8050,8080,8081,8082,8090/tcp
```

**2. Kontrollera att tjänster lyssnar:**
```bash
sudo netstat -tlnp | grep -E "8000|8050|8080|8081|8082|8090"
```

### Problem: "Requirement already satisfied" men Flask saknas

```bash
cd /home/kamp/fotbollsplan-bevattning
source .venv/bin/activate
pip install --force-reinstall flask flask-cors
```

---

## 📋 KOMPLETT CHECKLISTA

Efter installation ska följande vara klart:

### Python & Dependencies
- [x] Python 3.11+ installerat
- [x] Virtual environment (.venv) skapat
- [x] Alla Python-paket installerade (pymodbus, flask, fastapi, dash, etc.)

### I2C & Hårdvara
- [x] I2C aktiverat i /boot/config.txt
- [x] i2c-tools installerat
- [x] Kan köra `i2cdetect -y 1` utan fel

### Konfiguration
- [x] api_.env skapad och konfigurerad
- [x] API_KEY satt
- [x] MODBUS_HOST/PORT konfigurerat
- [x] SMTP konfigurerat (valfritt)
- [x] Superadmin-användare skapad
- [x] superadmin.txt har rättigheter 600

### Systemd Services (11 st)
- [x] bevattning-api (port 8000)
- [x] bevattning-controller
- [x] display-manager
- [x] unipi-modbus (port 502)
- [x] dashboard-hub (port 8090)
- [x] di-monitor (port 8081)
- [x] user-management (port 8082)
- [x] todo-checklist (port 8080)
- [x] dash-process-view (port 8050)
- [x] bevattning-scheduler (timer)

### Webbgränssnitt (6 st)
- [x] Dashboard Hub tillgänglig på port 8090
- [x] Bevattning API tillgänglig på port 8000
- [x] DI Monitor tillgänglig på port 8081
- [x] Användarhantering tillgänglig på port 8082
- [x] Process View tillgänglig på port 8050
- [x] TODO Checklist tillgänglig på port 8080

### Tailscale (valfritt)
- [ ] Tailscale installerat
- [ ] Tailscale konfigurerat och uppkopplat
- [ ] Kan nå gränssnitt via Tailscale-IP

---

## 🎉 KLAR FÖR DRIFT!

Om alla punkter är avcheckade:
1. **Öppna Dashboard Hub:** `http://<ip>:8090`
2. **Utforska systemet** genom att klicka på tjänstkorten
3. **Skapa användare** via Användarhantering
4. **Testa DI Monitor** genom att trycka på knappar
5. **Börja konfigurera** bevattningszoner och tider

**System 2.0 är redo!** 🚀

