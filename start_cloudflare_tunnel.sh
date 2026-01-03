#!/bin/bash
# Start Cloudflare Tunnel med gratis URL för Dashboard Hub
# Detta exponerar port 8090 (Dashboard Hub) som är huvudingången

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Startar Cloudflare Tunnel...                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Detta exponerar Dashboard Hub (port 8090) via en gratis URL."
echo "Från Dashboard Hub kan du nå alla andra funktioner."
echo ""
echo "URL:en visas nedan när tunneln startar."
echo "Kopiera URL:en och öppna den i din webbläsare!"
echo ""
echo "Tryck Ctrl+C för att stoppa tunneln."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Starta tunnel för Dashboard Hub (port 8090)
cloudflared tunnel --url http://localhost:8090

