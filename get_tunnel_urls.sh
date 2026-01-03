#!/bin/bash
# Hämtar URL:er för alla Cloudflare Tunnels

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   CLOUDFLARE TUNNEL URL:ER                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

if [ ! -d "/tmp/cloudflared_tunnels" ]; then
    echo "Inga tunnlar körs. Starta dem med:"
    echo "  ./start_all_cloudflare_tunnels.sh"
    exit 1
fi

echo "📊 Dashboard Hub:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/dashboard.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Ingen URL hittad"

echo ""
echo "🔌 DI Monitor:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/di.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Ingen URL hittad"

echo ""
echo "📊 Process View:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/process.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Ingen URL hittad"

echo ""
echo "👥 Användarhantering:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/users.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Ingen URL hittad"

echo ""
echo "💧 API:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/api.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Ingen URL hittad"

echo ""
echo "📋 TODO Checklist:"
grep -E "https://.*trycloudflare" /tmp/cloudflared_tunnels/todo.log 2>/dev/null | tail -1 | sed 's/.*\(https:\/\/[^ ]*\).*/\1/' || echo "  Ingen URL hittad"

echo ""

