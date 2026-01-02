#!/bin/bash
# Arkivera obsoleta filer från System 1.0

set -e

PROJECT_DIR="/home/kamp/fotbollsplan-bevattning"
cd "$PROJECT_DIR"

echo "🗂️  Arkiverar obsoleta filer..."

# Skapa arkivmappar
mkdir -p archive/old_scripts
mkdir -p archive/old_ui
mkdir -p archive/demos
mkdir -p archive/backups

# Flytta filer
echo "📦 Flyttar installationsskript..."
mv install_complete.py archive/old_scripts/ 2>/dev/null || true
mv setup.py archive/old_scripts/ 2>/dev/null || true

echo "📦 Flyttar gamla UI-versioner..."
mv dash_app_v2.broken archive/old_ui/ 2>/dev/null || true
mv dash_app_v2.old archive/old_ui/ 2>/dev/null || true

echo "📦 Flyttar demo-skript..."
mv demo_logging.py archive/demos/ 2>/dev/null || true
mv demo_user_management.py archive/demos/ 2>/dev/null || true

echo "📦 Flyttar backups..."
mv api_main.py.modbus_backup archive/backups/ 2>/dev/null || true

echo "📦 Flyttar obsolet dokumentation..."
mv COPILOT_WORKSPACE_GUIDE.md archive/old_documentation/ 2>/dev/null || true
mv ARCADE_BUTTONS.md archive/old_documentation/ 2>/dev/null || true

echo ""
echo "✅ Arkivering klar!"
echo ""
echo "Arkiverade filer finns i:"
find archive/ -type f | sort | sed 's/^/  - /'
echo ""
echo "📊 Sammanfattning:"
echo "  Root-filer innan: $(git ls-files | wc -l)"
echo "  Arkiverade: $(find archive/ -type f | wc -l)"
