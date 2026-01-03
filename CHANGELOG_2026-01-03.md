# Changelog - 2026-01-03

## 🎉 Stora förbättringar och nya funktioner

**System 2.0 - Webbgränssnitt och Dashboard Hub**

---

## ✨ NYA FUNKTIONER

### 🏠 Dashboard Hub (Port 8090)
- **Central startsida** för alla webbgränssnitt
- Snabb systemöversikt (zon, pump, läge, larm)
- Larm-notiser (pulserar vid kritiska larm)
- Länkar till alla andra gränssnitt
- Tjänstestatus (online/offline)
- Auto-uppdatering var 2:a sekund
- Responsiv design (mobil + desktop)

### 🔌 DI Monitor (Port 8081)
- **Realtidsövervakning** av alla 12 digitala ingångar
- Uppdatering var 0.5 sekund (snabbast!)
- Färgkodning: Grön=OK, Gul=Aktiv, Röd=Larm
- Perfekt för att testa knappar och sensorer
- Visar råvärden (GPIO HIGH/LOW)
- Kritiska larm pulserar

### 👥 Användarhantering (Port 8082)
- **Webb-UI för användaradministration**
- Skapa användare (enkelt formulär)
- Ta bort användare (knapp)
- Roller: Admin eller Operatör
- Ingen curl-kommandon behövs längre!
- Säker inloggning (superadmin)

---

## 🔧 FÖRBÄTTRINGAR

### Bevattning API (Port 8000)
- ✅ Modern design med gradient-header
- ✅ Snabbstatistik-kort överst
- ✅ DI-status integrerad (viktiga ingångar)
- ✅ Länkar till DI Monitor i header
- ✅ Snabbare uppdatering (5s → 2s)
- ✅ Bättre visuell feedback

### Display Manager
- ✅ Förbättrad boot-hantering (5s delay istället för 2s)
- ✅ Fler retry-försök (3 → 5)
- ✅ Aggressiv clear-sekvens (3x clear)
- ✅ I2C-bussverifiering före init
- ✅ Hard reset (backlight off/on)
- ✅ Förbättrade delays för stabilitet

### Alla Webbgränssnitt
- ✅ Responsiv design (mobil + desktop)
- ✅ Automatisk anpassning till skärmstorlek
- ✅ Större knappar på mobil
- ✅ Touch-optimerat
- ✅ Viewport meta-tags

---

## 🐛 BUGFIXAR

### Kritiska problem lösta
- ✅ **Disk 100% full** → 2.1GB frigjort (Timeshift-snapshots raderade)
- ✅ **Pymodbus korrupt** → Återinstallerat (skadades när disk blev full)
- ✅ **Pymodbus 3.x syntax** → `slave=` → `device_id=`
- ✅ **Dubblerade systemd-tjänster** → Stoppade och inaktiverade
- ✅ **Display-problem vid boot** → Robusta timings implementerade

---

## 📦 DEPENDENCIES UPPDATERADE

### Nya Python-paket:
```
flask>=2.3.0
flask-cors>=4.0.0
dash-bootstrap-components>=1.0.0
```

### requirements.txt och api_requirements.txt uppdaterade
Alla dependencies för nya webbgränssnitt inkluderade

---

## 🔧 INSTALLATIONS-PROCESSEN UPPDATERAD

### setup.sh förbättringar:
- ✅ Installerar alla 11 systemd-tjänster automatiskt
- ✅ Aktiverar alla nya webbgränssnitt
- ✅ Uppdaterad slutsammanfattning med länkar
- ✅ Visar Dashboard Hub som startsida

### Nya systemd-tjänster:
- `dashboard-hub.service` (port 8090)
- `di-monitor.service` (port 8081)
- `user-management.service` (port 8082)

---

## 📚 DOKUMENTATION

### Nya filer:
- ✅ **WEBBGRANSSNITT_GUIDE.md** - Komplett guide för alla webbgränssnitt
- ✅ **INSTALLATION_VERIFICATION.md** - Checklista efter installation
- ✅ **QUICK_START.md** - 30-sekunder snabbstart
- ✅ **CHANGELOG_2026-01-03.md** - Denna fil

### Uppdaterade filer:
- ✅ **README.md** - Webbgränssnitt-sektion tillagd
- ✅ **TAILSCALE_ACCESS.md** - Alla 6 webbgränssnitt med Tailscale-IP
- ✅ **setup.sh** - Installerar alla nya tjänster

---

## 🎯 VAD SOM ÄR NYTT FÖR ANVÄNDAREN

### Tidigare (krångligt):
```bash
# Starta zon 1
curl -X POST -H "X-API-Key: xxx" http://ip:8000/command/manual -d '{"zone":1}'

# Skapa användare
curl -X POST http://ip:8000/users/create -u superadmin:pass -d '{"username":"op1"...}'

# Se DI-status
python3 test_di_monitor.py
```

### Nu (enkelt):
```
1. Öppna: http://ip:8090
2. Klicka på tjänst
3. Gör vad du vill (klick och formulär)
```

**EN startsida → Allt annat via klick!**

---

## 🔢 SIFFROR

### Före idag:
- 3 webbgränssnitt
- Krånglig användarhantering (curl)
- Ingen DI-övervakning i webb
- Inget centralt dashboard
- Display-problem vid omstart

### Efter idag:
- **6 webbgränssnitt** (3 nya!)
- **Enkel användarhantering** (webb-UI)
- **Live DI-övervakning** (0.5s uppdatering)
- **Central Dashboard Hub** (startsida)
- **Stabil display-init** (5s delay + retry)
- **2.1GB diskutrymme** frigjort
- **Responsiv design** (mobil + desktop)
- **11 systemd-tjänster** auto-startar

---

## 🚀 NÄSTA STEG

Vid nästa installation (ny Raspberry Pi):
```bash
bash setup.sh
# → Alla 6 webbgränssnitt installeras automatiskt!
# → Allt klart efter omstart!
```

---

## 👏 RESULTAT

**Systemet är nu:**
- ✅ Mycket enklare att använda
- ✅ Mobilvänligt
- ✅ Professionellt
- ✅ Väldo dokumenterat
- ✅ Redo för drift

**Från krångliga curl-kommandon → Modern webbapplikation!** 🎉

---

**Skapad:** 2026-01-03  
**Systemversion:** 2.0  
**Plattform:** Raspberry Pi + UniPi 1.1

