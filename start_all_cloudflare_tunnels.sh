#!/bin/bash
# Startar Cloudflare Tunnels för alla tjänster
# Varje tjänst får sin egen tunnel-URL

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Startar Cloudflare Tunnels för alla tjänster...             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Stoppa eventuella befintliga tunnlar
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 2

# Skapa loggkatalog
mkdir -p /tmp/cloudflared_tunnels

echo "Startar tunnlar för:"
echo "  • Dashboard Hub (port 8090)"
echo "  • DI Monitor (port 8081)"
echo "  • Process View (port 8050)"
echo "  • Användarhantering (port 8082)"
echo "  • API (port 8000)"
echo "  • TODO Checklist (port 8080)"
echo ""
echo "Detta kan ta 10-30 sekunder..."
echo ""

# Starta tunnlar i bakgrunden
nohup cloudflared tunnel --url http://localhost:8090 > /tmp/cloudflared_tunnels/dashboard.log 2>&1 &
sleep 3

nohup cloudflared tunnel --url http://localhost:8081 > /tmp/cloudflared_tunnels/di.log 2>&1 &
sleep 3

nohup cloudflared tunnel --url http://localhost:8050 > /tmp/cloudflared_tunnels/process.log 2>&1 &
sleep 3

nohup cloudflared tunnel --url http://localhost:8082 > /tmp/cloudflared_tunnels/users.log 2>&1 &
sleep 3

nohup cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared_tunnels/api.log 2>&1 &
sleep 3

nohup cloudflared tunnel --url http://localhost:8080 > /tmp/cloudflared_tunnels/todo.log 2>&1 &
sleep 5

echo "Tunnlar startar... Väntar 10 sekunder för att få URL:er..."
sleep 10

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "URL:ER FÖR ALLA TJÄNSTER:"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Hämta URL:er från loggarna
echo "📊 Dashboard Hub:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/dashboard.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Startar..."

echo ""
echo "🔌 DI Monitor:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/di.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Startar..."

echo ""
echo "📊 Process View:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/process.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Startar..."

echo ""
echo "👥 Användarhantering:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/users.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Startar..."

echo ""
echo "💧 API:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/api.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Startar..."

echo ""
echo "📋 TODO Checklist:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/todo.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Startar..."

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "VIKTIGT:"
echo "  • URL:erna kan ta 10-30 sekunder att bli tillgängliga"
echo "  • Kör detta kommando igen om URL:erna inte visas:"
echo "    ./get_tunnel_urls.sh"
echo ""
echo "FÖR ATT SE LOGGARNA:"
echo "  tail -f /tmp/cloudflared_tunnels/*.log"
echo ""
echo "FÖR ATT STOPPA ALLA TUNNLAR:"
echo "  pkill -f 'cloudflared tunnel'"
echo ""

