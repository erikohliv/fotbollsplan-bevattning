# Tailscale Fjärråtkomst

## Tailscale IP-adress
```
100.124.254.103
```

## Tjänster du kan nå från jobbet

### 1. FastAPI (Huvudgränssnitt)
```
http://100.124.254.103:8000
```
- API-dokumentation: `http://100.124.254.103:8000/docs`
- Health check: `http://100.124.254.103:8000/health`

### 2. Dash Process View (Visualisering)
```
http://100.124.254.103:8050
```
- Realtidsöversikt av systemstatus
- Modbus-register, pumptillstånd, sensorer

### 3. SSH (Terminalåtkomst)
```bash
ssh kamp@100.124.254.103
```

## Tjänster som körs

| Tjänst | Port | Status | Autostart |
|--------|------|--------|-----------|
| bevattning-api | 8000 | ✅ | Ja |
| unipi-modbus | 502 | ✅ | Ja |
| dash-process-view | 8050 | ✅ | Ja |
| display-manager | - | ✅ | Ja |
| bevattning-controller | - | ✅ | Ja |

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
