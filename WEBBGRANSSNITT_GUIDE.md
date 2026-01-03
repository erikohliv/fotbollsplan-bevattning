# Webbgränssnitt Guide - Fotbollsplan Bevattning

**Uppdaterad:** 2026-01-03  
**System:** Version 2.0  

---

## 🏠 ÖVERSIKT

Systemet har **6 webbgränssnitt** för komplett styrning och övervakning. Alla är responsiva och fungerar på både mobil och desktop.

### Snabb navigation
Börja alltid på **Dashboard Hub** → Klicka dig vidare till det du behöver!

---

## 📱 ÅTKOMST

### 1. Lokalt (samma nätverk som Raspberry Pi)
```
http://<raspberry-pi-ip>:PORT
```
Hitta IP: `hostname -I` på Raspberry Pi

**Exempel:** `http://10.219.1.116:8090`

### 2. Fjärråtkomst via Tailscale (för administratörer)
```
http://<tailscale-ip>:PORT
```
Hitta IP: `sudo tailscale ip -4` på Raspberry Pi

**Exempel:** `http://100.124.254.103:8090`

### 3. Via Cloudflare Tunnel (för slutanvändare)
```
https://<cloudflare-tunnel-url>/PATH
```

**Nginx Reverse Proxy - Alla tjänster via samma URL:**
- Dashboard Hub: `https://<url>/`
- DI Monitor: `https://<url>/di`
- Process View: `https://<url>/process`
- Användarhantering: `https://<url>/users`
- API: `https://<url>/api`
- TODO Checklist: `https://<url>/todo`

**Exempel:** `https://scan-mode-laws-constantly.trycloudflare.com/`

**Fördelar:**
- ✅ Ingen VPN behövs
- ✅ Fungerar från vilken webbläsare som helst
- ✅ Fungerar på mobil och dator

---

## 🏠 1. DASHBOARD HUB (Port 8090)

**URL:** `http://<ip>:8090`  
**Syfte:** Central startsida och översikt  
**Rekommendation:** ⭐ **BÖRJA HÄR!**

### Funktioner
- ✅ Snabb systemöversikt (zon, pump, läge, larm)
- ✅ Länkar till alla andra gränssnitt
- ✅ Tjänstestatus (online/offline för alla services)
- ✅ Larm-notiser (pulserar vid kritiskt läge)
- ✅ Auto-uppdatering var 2:a sekund
- ✅ Responsiv design (mobil + desktop)

### Vad du ser
**Överst:** 4 statuskort
- Aktiv Zon
- Pump Status (grön när på)
- Driftläge (Auto/Manuell)
- Antal larm

**Larm-sektion:** Visas endast om larm finns
- Kritiska larm: Röd bakgrund, pulserar
- Normala larm: Gul bakgrund

**Tjänstekort:** 5 kort med länkar
- DI Monitor
- Bevattning API
- Användarhantering
- Process View
- TODO Checklist

### Användning
1. Öppna Dashboard Hub
2. Se snabb översikt
3. Klicka på tjänst du vill använda
4. Navigera tillbaka eller använd header-länkar

---

## 💧 2. BEVATTNING API (Port 8000)

**URL:** `http://<ip>:8000`  
**Syfte:** Huvudstyrning och konfiguration  
**Användning:** Daglig drift och styrning

### Funktioner
- ✅ Starta/stoppa enskilda zoner
- ✅ Starta natt-program (alla zoner)
- ✅ Konfigurera bevattningstider
- ✅ Sensor-fallback vid fel
- ✅ Zon-exkludering (inaktivera trasiga zoner)
- ✅ Test-bevattning (försäsongskontroll)
- ✅ Lägesval (Auto/Manuell)
- ✅ Felsökning och felåterställning
- ✅ Länkar till DI Monitor i header

### Uppdatering
- System status: var 2:a sekund
- DI-status: varje sekund

### Säkerhet
- Kräver API-nyckel (lagras i browser localStorage)
- Första gången: ange API-nyckel (från `api_.env`)

---

## 🔌 3. DI MONITOR (Port 8081)

**URL:** `http://<ip>:8081`  
**Syfte:** Realtidsövervakning av knappar och sensorer  
**Användning:** Test, diagnostik, felsökning

### Funktioner
- ✅ Visar alla 12 digitala ingångar (DI1-DI12) live
- ✅ Uppdatering var 0.5 sekund (snabbast!)
- ✅ Färgkodning:
  - Grön = OK/Inaktiv
  - Gul = Aktiv/Tryckt
  - Röd = Larm
  - Mörkröd = Kritiskt larm (pulserar)
- ✅ Visar råvärden (GPIO HIGH/LOW)
- ✅ Information om varje ingång (typ, beskrivning, noteringar)

### Användning
**Testa knappar:**
1. Öppna DI Monitor
2. Tryck på en knapp (t.ex. Startknapp)
3. Se DI2 bli gul direkt ("TRYCKT")
4. Släpp knapp → blir grön igen ("OK")

**Övervaka larm:**
- Nödstopp (DI3) → Röd om aktiverat
- Motorskydd (DI10) → Röd om utlöst
- Tryckvakt (DI9) → Status visas
- Flödesvakt (DI7) → Status visas

**Perfekt för felsökning!**

---

## 👥 4. ANVÄNDARHANTERING (Port 8082)

**URL:** `http://<ip>:8082`  
**Syfte:** Skapa och hantera användarkonton  
**Användning:** Administration (superadmin)

### Funktioner
- ✅ Skapa nya användare (enkelt formulär)
- ✅ Ta bort användare
- ✅ Visa alla användarkonton
- ✅ Roller: Admin eller Operatör
- ✅ Säker inloggning (HTTP Basic Auth)

### Första inloggning
```
Användarnamn: superadmin
Lösenord: (ditt superadmin-lösenord från installation)
```

### Skapa ny användare
1. Logga in som superadmin
2. Fyll i formulär:
   - Användarnamn (minst 3 tecken)
   - Lösenord (minst 8 tecken)
   - Bekräfta lösenord
   - Roll: Operatör eller Admin
3. Klicka "Skapa användare"
4. ✅ Klar!

### Ta bort användare
1. Hitta användare i listan
2. Klicka "🗑️ Ta bort"
3. Bekräfta
4. ✅ Borttagen!

**Superenkelt - inget curl-kommando behövs!**

---

## 📊 5. PROCESS VIEW (Port 8050)

**URL:** `http://<ip>:8050`  
**Syfte:** Grafisk visualisering med fotbollsplan  
**Användning:** Övervakning och analys

### Funktioner
- ✅ Fotbollsplan med zonöversikt
- ✅ Regnprognos (nästa 24h)
- ✅ Regnhistorik (senaste 7 dagar)
- ✅ Live processtatus
- ✅ Miljödata (markfukt, temperatur)
- ✅ Dash-baserad (Plotly)

---

## 📋 6. TODO CHECKLIST (Port 8080)

**URL:** `http://<ip>:8080`  
**Syfte:** Projekthantering och checklista  
**Användning:** Installation och test-tracking

### Funktioner
- ✅ Installation-checklista
- ✅ Hårdvaru-uppgifter
- ✅ Test-uppgifter
- ✅ Progress-bar
- ✅ Kontaktinformation

---

## 🎯 REKOMMENDERAD ARBETSFLÖDE

### Daglig drift
1. Öppna **Dashboard Hub** (8090)
2. Se snabb översikt
3. Vid behov → Klicka på relevant tjänst

### Test av hårdvara
1. Öppna **DI Monitor** (8081)
2. Tryck på knappar → Se status ändras live
3. Kontrollera att allt fungerar

### Skapa användare
1. Öppna **Dashboard Hub** (8090)
2. Klicka "Användarhantering"
3. Logga in som superadmin
4. Fyll i formulär → Skapa

### Felsökning
1. **Dashboard Hub** (8090) → Se larm-översikt
2. **DI Monitor** (8081) → Se vilka ingångar som larmar
3. **Bevattning API** (8000) → Felsökning-knapp för detaljer

---

## 📱 MOBIL-ANVÄNDNING

Alla gränssnitt är **responsiva** och fungerar perfekt på mobil:

### På mobil (smartphone/tablet)
- ✅ Automatisk anpassning till skärmstorlek
- ✅ Större knappar för fingrar
- ✅ Större text för läsbarhet
- ✅ En kolumn (istället för flera)
- ✅ Touch-optimerad

### På desktop
- ✅ Flera kolumner
- ✅ Hover-effekter
- ✅ Kompakt layout
- ✅ Mer information synlig

**Samma webbadress fungerar på båda!**

---

## 🔒 SÄKERHET

### API-nyckel (Bevattning API)
- Krävs för att använda Bevattning API (port 8000)
- Sparas i webbläsaren (localStorage)
- Konfigureras i `api_.env`

### Superadmin-inloggning (Användarhantering)
- Krävs för att hantera användare (port 8082)
- HTTP Basic Authentication
- Lösenord hashat med bcrypt

### Tailscale
- Krypterad åtkomst (WireGuard)
- Endast dina enheter kan nå systemet
- Ingen exponering mot internet

---

## 🔧 FELSÖKNING

### Kan inte nå webbgränssnitten?

**1. Kontrollera tjänststatus:**
```bash
systemctl status dashboard-hub bevattning-api di-monitor
```

**2. Kontrollera portar:**
```bash
netstat -tlnp | grep -E "8000|8050|8080|8081|8082|8090"
```

**3. Starta om tjänster:**
```bash
sudo systemctl restart dashboard-hub bevattning-api di-monitor user-management
```

### Tailscale fungerar inte?

**1. Kontrollera status:**
```bash
tailscale status
```

**2. Kontrollera att Tailscale körs:**
```bash
sudo systemctl status tailscaled
```

**3. Logga in igen om behövs:**
```bash
sudo tailscale up
```

### Dashboard Hub visar "Offline" för tjänst?

**1. Kontrollera om tjänsten körs:**
```bash
systemctl is-active <tjänst-namn>
```

**2. Starta tjänsten:**
```bash
sudo systemctl start <tjänst-namn>
```

---

## 📊 PORTAR - SAMMANFATTNING

| Port | Tjänst | Syfte | Autostart |
|------|--------|-------|-----------|
| **8090** | Dashboard Hub | **Startsida** | ✅ |
| 8000 | Bevattning API | Huvudstyrning | ✅ |
| 8081 | DI Monitor | Knapp/Sensor-övervakning | ✅ |
| 8082 | Användarhantering | Användaradmin | ✅ |
| 8050 | Process View | Grafisk vy | ✅ |
| 8080 | TODO Checklist | Projektlista | ✅ |
| 502 | Modbus TCP | PLC-kommunikation | ✅ |

**Rekommendation:** Bokmärk Dashboard Hub (8090) som startsida!

---

## 🚀 SNABBSTART

### Första gången
1. Hitta Raspberry Pi:s IP: `hostname -I`
2. Öppna Dashboard Hub: `http://<ip>:8090`
3. Klicka runt och utforska!

### Med Tailscale från jobbet/mobil
1. Installera Tailscale på din enhet
2. Logga in (samma konto som Raspberry Pi)
3. Öppna: `http://100.124.254.103:8090`
4. Nu kan du styra bevattningen hemifrån jobbet! 🎉

---

## 💡 TIPS

- **Bokmärk Dashboard Hub** - din nya startsida
- **Använd DI Monitor** för att testa hårdvara
- **Bevattning API** för daglig drift
- **Dashboard på mobil** fungerar perfekt via Tailscale
- **Lägg till genväg på hemskärm** (mobil) för snabb åtkomst

---

## 🆘 SUPPORT

Om något inte fungerar:
1. Kontrollera [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Se [INSTALLATION.md](INSTALLATION.md) för ominstallation
3. Kolla loggar: `journalctl -u <tjänst-namn> -f`

