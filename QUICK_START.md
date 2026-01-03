# Quick Start Guide - Fotbollsplan Bevattning

**För dig som redan installerat systemet och vill komma igång snabbt!**

---

## 🚀 30-SEKUNDER START

### 1. Hitta din Raspberry Pi:s IP
```bash
hostname -I
```

### 2. Öppna Dashboard Hub i webbläsare
```
http://<din-ip>:8090
```

### 3. Klicka runt!
- Se systemöversikt
- Klicka på "DI Monitor" → Testa knappar
- Klicka på "Användarhantering" → Skapa användare
- Klicka på "Bevattning API" → Styr zoner

**KLART!** 🎉

---

## 📱 FRÅN MOBIL (via Tailscale)

### 1. Installera Tailscale på mobilen
- iPhone: App Store → "Tailscale"
- Android: Play Store → "Tailscale"

### 2. Logga in (samma konto som Raspberry Pi)

### 3. Öppna Dashboard Hub
```
http://100.124.254.103:8090
```

**Nu kan du styra bevattningen från var som helst!** 🌍

---

## 💧 VANLIGA ÅTGÄRDER

### Starta bevattning på en zon:
1. Dashboard Hub → "Bevattning API"
2. Välj zon i dropdown
3. Klicka "Starta Zon"

### Testa en knapp:
1. Dashboard Hub → "DI Monitor"
2. Tryck på fysisk knapp
3. Se status ändras live (blir gul)

### Skapa ny användare:
1. Dashboard Hub → "Användarhantering"
2. Logga in med superadmin
3. Fyll i formulär
4. Klicka "Skapa användare"

### Se systemstatus:
1. Öppna Dashboard Hub
2. Se snabbstatistik överst
3. Larm visas automatiskt om något är fel

---

## 🔍 FELSÖKNING - 3 STEG

### Steg 1: Kolla Dashboard Hub
```
http://<ip>:8090
```
Ser du "🔴 Offline" på något kort? → Tjänsten körs inte

### Steg 2: Starta om tjänsten
```bash
sudo systemctl restart <tjänst-namn>
```

### Steg 3: Kolla loggar
```bash
journalctl -u <tjänst-namn> -n 50
```

---

## 📚 MER HJÄLP

- **Översikt:** [README.md](README.md)
- **Webbgränssnitt:** [WEBBGRANSSNITT_GUIDE.md](WEBBGRANSSNITT_GUIDE.md)
- **Tailscale:** [TAILSCALE_ACCESS.md](TAILSCALE_ACCESS.md)
- **Installation:** [INSTALL_SYSTEM2.md](INSTALL_SYSTEM2.md)

---

## 🎯 BOKMÄRK DESSA

### Desktop:
```
http://<ip>:8090  (Dashboard Hub)
```

### Mobil (Tailscale):
```
http://100.124.254.103:8090
```

**Sparas som favorit/hemskärm för snabb åtkomst!**

---

**Lycka till med bevattningen! 💧🏟️**

