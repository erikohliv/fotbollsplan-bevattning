#!/bin/bash
###############################################################################
# verify.sh - Fotbollsplan Bevattning System 2.0 Verification Script
#
# Detta script verifierar att systemet är korrekt installerat och konfigurerat.
#
# Kontrollerar:
# - Virtual environment (.venv) existerar
# - Python-beroenden (pymodbus, smbus2, passlib, fastapi, requests)
# - Konfigurationsfiler (api_.env, superadmin.txt)
# - I2C-enheter (0x27 Display 1, 0x20 Arkadknappar) - med --skip-i2c flagga
# - systemd services (bevattning-controller, display-manager, bevattning-api)
# - Kritiska filer (bevattning_controller.py, display_manager.py, etc.)
#
# Användning:
#   bash verify.sh [--skip-i2c]
#
# Exit codes:
#   0 - Alla kontroller OK
#   1 - En eller flera kontroller misslyckades
#
###############################################################################

# Färgkoder
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Räknare för fel
ERRORS=0
WARNINGS=0

# Flaggor
SKIP_I2C=0

# Parse arguments
for arg in "$@"; do
    case $arg in
        --skip-i2c)
            SKIP_I2C=1
            shift
            ;;
    esac
done

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_check() {
    echo -n "  Kontrollerar $1... "
}

print_ok() {
    echo -e "${GREEN}OK${NC}"
}

print_fail() {
    echo -e "${RED}MISSLYCKADES${NC}"
    ERRORS=$((ERRORS + 1))
}

print_warning() {
    echo -e "${YELLOW}VARNING${NC}"
    WARNINGS=$((WARNINGS + 1))
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Hitta projektmapp
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)
if [[ -z "$PROJECT_DIR" ]]; then
    PROJECT_DIR=$(pwd)
fi

print_header "Fotbollsplan Bevattning System 2.0 - Verifiering"
echo "Projektmapp: $PROJECT_DIR"
echo

# 1. Kontrollera Virtual Environment
print_header "1. Virtual Environment"

print_check ".venv"
if [[ -d "$PROJECT_DIR/.venv" ]]; then
    print_ok
else
    print_fail
    echo "    ${RED}✗${NC} .venv hittades inte i $PROJECT_DIR"
fi

print_check "Python i .venv"
if [[ -f "$PROJECT_DIR/.venv/bin/python3" ]]; then
    print_ok
    PYTHON_VERSION=$("$PROJECT_DIR/.venv/bin/python3" --version 2>&1)
    echo "    ${GREEN}✓${NC} $PYTHON_VERSION"
else
    print_fail
fi

# 2. Kontrollera Python-beroenden
print_header "2. Python-beroenden"

REQUIRED_PACKAGES=(
    "pymodbus"
    "smbus2"
    "passlib"
    "fastapi"
    "requests"
    "uvicorn"
    "dotenv:python-dotenv"
)

for PKG_SPEC in "${REQUIRED_PACKAGES[@]}"; do
    # Hantera pakettnamn som skiljer sig från import-namn
    IMPORT_NAME="${PKG_SPEC%%:*}"
    PKG_NAME="${PKG_SPEC##*:}"
    
    print_check "$PKG_NAME"
    if [[ -f "$PROJECT_DIR/.venv/bin/python3" ]]; then
        if "$PROJECT_DIR/.venv/bin/python3" -c "import ${IMPORT_NAME}" 2>/dev/null; then
            print_ok
        else
            print_fail
            echo "    ${RED}✗${NC} Kör: source .venv/bin/activate && pip install $PKG_NAME"
        fi
    else
        print_fail
        echo "    ${RED}✗${NC} .venv saknas"
    fi
done

# 3. Kontrollera konfigurationsfiler
print_header "3. Konfigurationsfiler"

print_check "api_.env"
if [[ -f "$PROJECT_DIR/api_.env" ]]; then
    print_ok
    
    # Kontrollera viktiga variabler
    REQUIRED_VARS=("API_KEY" "MODBUS_HOST" "MODBUS_PORT" "LATITUDE" "LONGITUDE")
    for VAR in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${VAR}=" "$PROJECT_DIR/api_.env"; then
            echo "    ${GREEN}✓${NC} $VAR är satt"
        else
            echo "    ${YELLOW}⚠${NC} $VAR saknas"
            WARNINGS=$((WARNINGS + 1))
        fi
    done
    
    # Kontrollera rättigheter
    PERMS=$(stat -c %a "$PROJECT_DIR/api_.env" 2>/dev/null || stat -f %A "$PROJECT_DIR/api_.env" 2>/dev/null)
    if [[ "$PERMS" == "600" ]]; then
        echo "    ${GREEN}✓${NC} Rättigheter: 600 (OK)"
    else
        echo "    ${YELLOW}⚠${NC} Rättigheter: $PERMS (rekommenderat: 600)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    print_fail
    echo "    ${RED}✗${NC} Skapa api_.env från api_.env.example"
fi

print_check "superadmin.txt"
if [[ -f "$PROJECT_DIR/superadmin.txt" ]]; then
    print_ok
    
    # Kontrollera rättigheter
    PERMS=$(stat -c %a "$PROJECT_DIR/superadmin.txt" 2>/dev/null || stat -f %A "$PROJECT_DIR/superadmin.txt" 2>/dev/null)
    if [[ "$PERMS" == "600" ]]; then
        echo "    ${GREEN}✓${NC} Rättigheter: 600 (OK)"
    else
        echo "    ${YELLOW}⚠${NC} Rättigheter: $PERMS (rekommenderat: 600)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    print_warning
    echo "    ${YELLOW}⚠${NC} superadmin.txt saknas (krävs för admin-åtkomst)"
fi

# 4. Kontrollera I2C-enheter (om inte --skip-i2c)
if [[ $SKIP_I2C -eq 0 ]]; then
    print_header "4. I2C-enheter"
    
    if command -v i2cdetect &> /dev/null; then
        print_check "Display 1 (0x27)"
        if i2cdetect -y 1 2>/dev/null | grep -q " 27 "; then
            print_ok
        else
            print_warning
            echo "    ${YELLOW}⚠${NC} Display 1 (0x27) hittades inte på I2C-bussen"
            echo "    ${YELLOW}⚠${NC} Kontrollera anslutning eller kör: i2cdetect -y 1"
        fi
        
        print_check "Arkadknappar (0x20)"
        if i2cdetect -y 1 2>/dev/null | grep -q " 20 "; then
            print_ok
        else
            print_warning
            echo "    ${YELLOW}⚠${NC} Arkadknappar (0x20) hittades inte på I2C-bussen"
            echo "    ${YELLOW}⚠${NC} Kontrollera anslutning eller kör: i2cdetect -y 1"
        fi
    else
        print_warning
        echo "    ${YELLOW}⚠${NC} i2cdetect inte installerat (installera: sudo apt install i2c-tools)"
    fi
else
    print_info "Hoppar över I2C-kontroll (--skip-i2c)"
fi

# 5. Kontrollera systemd services
print_header "5. systemd Services"

SERVICES=(
    "bevattning-controller.service"
    "bevattning-api.service"
    "display-manager.service"
)

for SERVICE in "${SERVICES[@]}"; do
    print_check "$SERVICE"
    
    if systemctl list-unit-files | grep -q "^${SERVICE}"; then
        # Service finns
        if systemctl is-enabled "$SERVICE" &>/dev/null; then
            print_ok
            echo "    ${GREEN}✓${NC} Enabled"
        else
            print_warning
            echo "    ${YELLOW}⚠${NC} Inte enabled (aktivera: sudo systemctl enable $SERVICE)"
        fi
        
        # Kontrollera status
        if systemctl is-active "$SERVICE" &>/dev/null; then
            echo "    ${GREEN}✓${NC} Körs nu"
        else
            echo "    ${BLUE}ℹ${NC} Körs inte (starta: sudo systemctl start $SERVICE)"
        fi
    else
        print_warning
        echo "    ${YELLOW}⚠${NC} Service-fil saknas i /etc/systemd/system/"
    fi
done

# 6. Kontrollera kritiska filer
print_header "6. Kritiska Filer"

CRITICAL_FILES=(
    "bevattning_controller.py"
    "display_manager.py"
    "hardware_map.csv"
    "user_management.py"
    "healthcheck.py"
    "api_main.py"
)

for FILE in "${CRITICAL_FILES[@]}"; do
    print_check "$FILE"
    if [[ -f "$PROJECT_DIR/$FILE" ]]; then
        print_ok
    else
        print_fail
        echo "    ${RED}✗${NC} $FILE saknas"
    fi
done

# Sammanfattning
print_header "Sammanfattning"

if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
    echo -e "${GREEN}✓ Alla kontroller OK!${NC}"
    echo
    echo "Systemet är redo att användas."
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    echo -e "${YELLOW}⚠ $WARNINGS varning(ar)${NC}"
    echo
    echo "Systemet fungerar men vissa delar saknas eller behöver uppmärksamhet."
    exit 0
else
    echo -e "${RED}✗ $ERRORS fel, $WARNINGS varning(ar)${NC}"
    echo
    echo "Systemet har allvarliga problem som måste åtgärdas."
    echo "Kör setup.sh för att installera saknade komponenter."
    exit 1
fi
