# Cloudflare Tunnel - Installationsguide

## Översikt

Cloudflare Tunnel ger säker publik åtkomst till ditt bevattningssystem utan att öppna portar i brandväggen. All trafik går genom Cloudflares nätverk och krypteras automatiskt med TLS.

## Förutsättningar

✅ `cloudflared` är redan installerad (version 2025.11.1)  
✅ Du behöver ett Cloudflare-konto (gratis)  
✅ Du behöver en domän (t.ex. `ik-kamp.se`)  
✅ Domänen måste vara konfigurerad i Cloudflare (DNS-servrar pekade till Cloudflare)

## Steg-för-steg Installation

### Steg 1: Logga in på Cloudflare

```bash
cloudflared tunnel login
```

**Vad händer:**
- En webbläsare öppnas automatiskt
- Du loggar in på ditt Cloudflare-konto
- Du väljer vilken domän tunneln ska använda
- En `cert.pem` fil skapas i `~/.cloudflared/`

**Tips:** Om du kör via SSH utan grafisk miljö, kopiera URL:en som visas och öppna den i en webbläsare på din dator.

---

### Steg 2: Skapa en tunnel

```bash
cloudflared tunnel create bevattning-ikkamp
```

**Vad händer:**
- En tunnel skapas med namnet `bevattning-ikkamp`
- Du får en **UUID** (t.ex. `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
- En credentials-fil skapas: `~/.cloudflared/<UUID>.json`

**Spara UUID:n!** Du behöver den i nästa steg.

---

### Steg 3: Skapa konfigurationsfil

```bash
# Skapa katalog om den inte finns
mkdir -p ~/.cloudflared

# Kopiera exempel-konfigurationen
cp cloudflare_tunnel_config_example.yml ~/.cloudflared/config.yml

# Redigera filen
nano ~/.cloudflared/config.yml
```

**Ersätt följande i filen:**
- `<TUNNEL-UUID>` → Din faktiska UUID från Steg 2
- `<TUNNEL-NAME>` → `bevattning-ikkamp` (eller vad du valde)
- `<YOUR-DOMAIN>` → Din domän (t.ex. `ik-kamp.se`)

**Exempel efter redigering:**
```yaml
tunnel: a1b2c3d4-e5f6-7890-abcd-ef1234567890
credentials-file: /home/kamp/.cloudflared/a1b2c3d4-e5f6-7890-abcd-ef1234567890.json

ingress:
  - hostname: bevattning.ik-kamp.se
    service: http://localhost:8090
  
  - hostname: di.ik-kamp.se
    service: http://localhost:8081
  
  # ... resten av reglerna
  
  - service: http_status:404
```

---

### Steg 4: Konfigurera DNS

För **varje** subdomän i din config.yml, kör:

```bash
cloudflared tunnel route dns bevattning-ikkamp bevattning.ik-kamp.se
cloudflared tunnel route dns bevattning-ikkamp di.ik-kamp.se
cloudflared tunnel route dns bevattning-ikkamp users.ik-kamp.se
cloudflared tunnel route dns bevattning-ikkamp api.ik-kamp.se
cloudflared tunnel route dns bevattning-ikkamp process.ik-kamp.se
cloudflared tunnel route dns bevattning-ikkamp todo.ik-kamp.se
```

**Vad händer:**
- DNS CNAME-poster skapas automatiskt i Cloudflare
- Alla subdomäner pekar nu på din tunnel

**Alternativ:** Du kan också skapa DNS-posterna manuellt i Cloudflare Dashboard:
- Typ: `CNAME`
- Namn: `bevattning` (eller `di`, `users`, etc.)
- Innehåll: `<TUNNEL-UUID>.cfargotunnel.com`
- Proxy status: Proxied (orange moln)

---

### Steg 5: Testa tunneln (innan installation)

```bash
cloudflared tunnel run bevattning-ikkamp
```

**Vad händer:**
- Tunneln startar i förgrunden
- Du ser loggmeddelanden
- Testa att besöka `https://bevattning.ik-kamp.se` i en webbläsare

**Om det fungerar:** Tryck `Ctrl+C` för att stoppa och fortsätt till Steg 6.

**Om det INTE fungerar:**
- Kontrollera att alla tjänster körs lokalt (port 8090, 8081, etc.)
- Kontrollera att config.yml är korrekt
- Kontrollera loggarna för felmeddelanden

---

### Steg 6: Installera som systemd-tjänst

```bash
# Installera tjänsten
sudo cloudflared service install

# Starta tjänsten
sudo systemctl start cloudflared

# Aktivera autostart vid omstart
sudo systemctl enable cloudflared

# Kontrollera status
sudo systemctl status cloudflared
```

**Vad händer:**
- En systemd-tjänst skapas
- Tunneln startar automatiskt vid systemstart
- Tunneln körs i bakgrunden

---

### Steg 7: Verifiera installation

```bash
# Kontrollera att tunneln körs
sudo systemctl status cloudflared

# Visa loggar
sudo journalctl -u cloudflared -f

# Lista alla tunnlar
cloudflared tunnel list

# Visa tunnel-info
cloudflared tunnel info bevattning-ikkamp
```

**Testa i webbläsare:**
- https://bevattning.ik-kamp.se (Dashboard Hub)
- https://di.ik-kamp.se (DI Monitor)
- https://users.ik-kamp.se (Användarhantering)
- https://api.ik-kamp.se (API)
- https://process.ik-kamp.se (Process View)
- https://todo.ik-kamp.se (TODO Checklist)

---

## Subdomäner och Tjänster

| Subdomän | Port | Tjänst | Beskrivning |
|----------|------|--------|-------------|
| `bevattning.<domain>` | 8090 | Dashboard Hub | Huvudingång, översikt |
| `di.<domain>` | 8081 | DI Monitor | Digital Input Monitoring |
| `users.<domain>` | 8082 | Användarhantering | Skapa/ta bort användare |
| `api.<domain>` | 8000 | API | REST API för styrning |
| `process.<domain>` | 8050 | Process View | Grafisk visualisering |
| `todo.<domain>` | 8080 | TODO Checklist | Projekthantering |

---

## Säkerhet

### Inloggning krävs
Alla tjänster är nu skyddade med inloggning:
- **Dashboard Hub, DI Monitor:** Flask-Login
- **Process View:** Dash BasicAuth
- **API:** API-nyckel + användarautentisering
- **Användarhantering:** Session-baserad autentisering

### TLS/HTTPS
- All trafik krypteras automatiskt av Cloudflare
- Certifikat hanteras automatiskt
- Ingen manuell certifikathantering behövs

### Ingen öppen port
- Inga portar behöver öppnas i brandväggen
- All trafik går genom Cloudflares nätverk
- Tunneln initierar utgående anslutning (inifrån och ut)

---

## Felsökning

### Tunneln startar inte
```bash
# Kontrollera loggar
sudo journalctl -u cloudflared -n 50

# Kontrollera konfiguration
cloudflared tunnel ingress validate
```

### DNS fungerar inte
```bash
# Lista DNS-routes
cloudflared tunnel route dns list

# Kontrollera i Cloudflare Dashboard
# → DNS → Records
```

### Tjänst inte nåbar
```bash
# Kontrollera att lokal tjänst körs
curl http://localhost:8090

# Kontrollera systemd-tjänster
systemctl --user list-units | grep bevattning
```

### Återställ tunnel
```bash
# Stoppa tjänsten
sudo systemctl stop cloudflared

# Ta bort tjänsten
sudo cloudflared service uninstall

# Ta bort tunnel
cloudflared tunnel delete bevattning-ikkamp

# Börja om från Steg 2
```

---

## Hantera tunneln

### Starta/stoppa tunneln
```bash
sudo systemctl start cloudflared
sudo systemctl stop cloudflared
sudo systemctl restart cloudflared
```

### Visa loggar
```bash
# Realtidsloggar
sudo journalctl -u cloudflared -f

# Senaste 100 rader
sudo journalctl -u cloudflared -n 100
```

### Uppdatera konfiguration
```bash
# Redigera config
nano ~/.cloudflared/config.yml

# Validera config
cloudflared tunnel ingress validate

# Starta om tjänsten
sudo systemctl restart cloudflared
```

### Ta bort tunnel
```bash
# Stoppa tjänsten
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared
sudo cloudflared service uninstall

# Ta bort DNS-routes
cloudflared tunnel route dns delete bevattning-ikkamp bevattning.ik-kamp.se
# (upprepa för alla subdomäner)

# Ta bort tunnel
cloudflared tunnel delete bevattning-ikkamp
```

---

## Alternativ: Path-baserad routing

Om du bara vill använda **EN** domän istället för flera subdomäner, kan du använda path-baserad routing.

**Exempel:** Alla tjänster under `bevattning.ik-kamp.se`:
- `bevattning.ik-kamp.se/` → Dashboard Hub
- `bevattning.ik-kamp.se/di` → DI Monitor
- `bevattning.ik-kamp.se/users` → Användarhantering
- etc.

Se `cloudflare_tunnel_config_example.yml` för exempel på path-baserad konfiguration.

**OBS:** Path-baserad routing kräver att dina Flask/Dash-appar är konfigurerade för att köra under en subpath (t.ex. `/di` istället för `/`). Detta kan kräva kodändringar.

---

## Kostnader

Cloudflare Tunnel är **gratis** för upp till 50 användare. Inga dolda kostnader.

---

## Support

- Cloudflare Tunnel dokumentation: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- Cloudflare Community: https://community.cloudflare.com/

---

## Sammanfattning

✅ **Säkert:** TLS-kryptering, ingen öppen port  
✅ **Enkelt:** Ingen manuell certifikathantering  
✅ **Gratis:** Upp till 50 användare  
✅ **Pålitligt:** Cloudflares globala nätverk  
✅ **Flexibelt:** Stöd för flera subdomäner eller path-baserad routing  

**Tailscale vs Cloudflare Tunnel:**
- **Tailscale:** Privat VPN, kräver Tailscale-klient på alla enheter
- **Cloudflare Tunnel:** Publik åtkomst via vanlig webbläsare, ingen klient behövs

**Rekommendation:** Använd **båda**!
- **Tailscale** för privat åtkomst (du och ditt team)
- **Cloudflare Tunnel** för publik åtkomst (externa användare, mobil utan VPN)

