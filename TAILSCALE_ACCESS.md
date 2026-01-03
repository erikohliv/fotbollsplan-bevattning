# Tailscale Fjärråtkomst

## Tailscale IP-adress
```
100.124.254.103
```

## Tjänster du kan nå från jobbet

### 🏠 Dashboard Hub (Startsida - REKOMMENDERAD)
```
http://100.124.254.103:8090
```
- Central kontrollpanel med översikt
- Länkar till alla andra gränssnitt
- Systemstatus och larm
- **STARTA HÄR** - härifrån når du allt annat!

### 💧 Bevattning API (Huvudstyrning)
```
http://100.124.254.103:8000
```
- Starta/stoppa zoner
- Konfigurera bevattningstider
- Sensor-fallback och zonhantering
- API-dokumentation: `http://100.124.254.103:8000/docs`

### 🔌 DI Monitor (Knapp/Sensor-övervakning)
```
http://100.124.254.103:8081
```
- Realtidsövervakning av digitala ingångar (DI1-DI12)
- Ser när knappar trycks (0.5s uppdatering)
- Larm-övervakning (nödstopp, motorskydd, etc.)

### 👥 Användarhantering
```
http://100.124.254.103:8082
```
- Skapa och ta bort användare
- Administrera roller (Admin/Operatör)
- Kräver superadmin-inloggning

### 📊 Process View (Grafisk visualisering)
```
http://100.124.254.103:8050
```
- Fotbollsplan med zonöversikt
- Regnprognos och väderdata
- Live processtatus

### 📋 TODO Checklist
```
http://100.124.254.103:8080
```
- Installation och test-checklista
- Projekthantering

### 🔧 SSH (Terminalåtkomst)
```bash
ssh kamp@100.124.254.103
```

## Tjänster som körs

| Tjänst | Port | Status | Autostart | Beskrivning |
|--------|------|--------|-----------|-------------|
| dashboard-hub | 8090 | ✅ | Ja | Central startsida |
| bevattning-api | 8000 | ✅ | Ja | Huvudstyrning |
| di-monitor | 8081 | ✅ | Ja | DI-övervakning |
| user-management | 8082 | ✅ | Ja | Användarhantering |
| dash-process-view | 8050 | ✅ | Ja | Grafisk visualisering |
| todo-checklist | 8080 | ✅ | Ja | Projektchecklista |
| unipi-modbus | 502 | ✅ | Ja | Modbus TCP-server |
| display-manager | - | ✅ | Ja | LCD-display |
| bevattning-controller | - | ✅ | Ja | Väder + logik |

## Kontrollera Tailscale-status
```bash
tailscale status
tailscale ip -4
```

## Starta om Tailscale (om behövs)
```bash
sudo systemctl restart tailscaled
sudo tailscale up
```

## Troubleshooting

### Kan inte nå tjänsterna?
1. Kontrollera att Tailscale är uppkopplat:
   ```bash
   tailscale status
   ```

2. Kontrollera att tjänsterna körs:
   ```bash
   systemctl status bevattning-api dash-process-view
   ```

3. Kontrollera att Tailscale är inloggat på DIN enhet (jobbet):
   - Installera Tailscale på jobbdatorn
   - Logga in med samma konto (erik.ohliv@gmail.com)
   - Du bör se `fotbollsplan-plc-1` i din enhetslista

### Tailscale loggar ut automatiskt?
Aktivera autostart:
```bash
sudo systemctl enable tailscaled
```

## Säkerhet
- ✅ Tailscale använder WireGuard (krypterat)
- ✅ Endast dina enheter kan nå systemet
- ✅ Ingen exponering mot internet
- ⚠️ Se till att din jobbdator har Tailscale installerat och inloggat

---
**Senast uppdaterat:** 2026-01-01
**Tailscale hostname:** fotbollsplan-plc-1
