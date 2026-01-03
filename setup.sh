#!/bin/bash
###############################################################################
# setup.sh - Fotbollsplan Bevattning System 2.0 Installation Script
#
# Detta script installerar och konfigurerar bevattningssystemet på Raspberry Pi 4
# med Raspberry Pi OS (Debian Bookworm).
#
# Funktioner:
# - Kontrollerar system och internet-anslutning
# - Installerar systempaket (python3, i2c-tools, git, etc.)
# - Aktiverar I2C för Display 1 (0x27) och Arkadknappar (0x20)
# - Skapar Python virtual environment (.venv)
# - Installerar alla beroenden från requirements.txt
# - Konfigurerar api_.env interaktivt (Modbus, API_KEY, SMTP)
# - Skapar superadmin-användare med bcrypt-hashing
# - Installerar Tailscale (valfritt)
# - Installerar systemd services
# - Kör post-installation verification
# - Erbjuder hardware-tester
#
# Användning:
#   bash setup.sh
#   eller
#   curl -fsSL https://raw.githubusercontent.com/erikohliv/fotbollsplan-bevattning/main/setup.sh | bash
#
###############################################################################

set -e  # Exit on error

# Färgkoder för output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default-värden
DEFAULT_LATITUDE="56.05"
DEFAULT_LONGITUDE="14.40"
DEFAULT_MODBUS_HOST="127.0.0.1"
DEFAULT_MODBUS_PORT="502"
DEFAULT_MODBUS_UNIT="1"
DEFAULT_SMTP_HOST="smtp.gmail.com"
DEFAULT_SMTP_PORT="587"
DISPLAY_1_I2C_ADDRESS="0x27"
I2C_BUTTON_ADDRESS="0x20"

# Hjälpfunktioner
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Kontrollera om script körs som root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Detta script måste köras som root (använd sudo)"
        echo "Användning: sudo bash setup.sh"
        exit 1
    fi
}

# Kontrollera om vi är på Raspberry Pi
check_raspberry_pi() {
    print_info "Kontrollerar Raspberry Pi..."
    if [[ ! -f /proc/device-tree/model ]]; then
        print_warning "Kunde inte verifiera Raspberry Pi-modell"
        read -p "Vill du fortsätta ändå? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[YyJj]$ ]]; then
            exit 1
        fi
    else
        MODEL=$(cat /proc/device-tree/model)
        print_success "Raspberry Pi modell: $MODEL"
    fi
}

# Kontrollera internet-anslutning
check_internet() {
    print_info "Kontrollerar internet-anslutning..."
    if ping -c 1 -W 5 8.8.8.8 &> /dev/null; then
        print_success "Internet-anslutning OK"
        return 0
    else
        print_error "Ingen internet-anslutning"
        return 1
    fi
}

# Installera systempaket
install_system_packages() {
    print_header "Systempaket Installation"
    
    print_info "Uppdaterar paketlistan..."
    apt update || {
        print_error "Kunde inte uppdatera paketlistan"
        return 1
    }
    
    print_info "Installerar systempaket..."
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-smbus \
        i2c-tools \
        git \
        curl \
        build-essential \
        || {
        print_error "Paketinstallation misslyckades"
        return 1
    }
    
    print_success "Systempaket installerade"
}

# Aktivera I2C
enable_i2c() {
    print_header "I2C Aktivering"
    
    print_info "Aktiverar I2C för Display 1 (${DISPLAY_1_I2C_ADDRESS}) och Arkadknappar (${I2C_BUTTON_ADDRESS})..."
    
    # Använd raspi-config om tillgängligt
    if command -v raspi-config &> /dev/null; then
        raspi-config nonint do_i2c 0 || print_warning "raspi-config misslyckades"
    fi
    
    # Säkerställ att i2c-dev är i /etc/modules
    if ! grep -q "^i2c-dev" /etc/modules; then
        echo "i2c-dev" >> /etc/modules
        print_success "Lade till i2c-dev i /etc/modules"
    fi
    
    # Ladda i2c-dev nu
    modprobe i2c-dev 2>/dev/null || print_warning "Kunde inte ladda i2c-dev modul"
    
    # Lägg till användare i i2c-gruppen
    USER=${SUDO_USER:-pi}
    usermod -a -G i2c "$USER" || print_warning "Kunde inte lägga till $USER i i2c-grupp"
    
    print_success "I2C aktiverat"
    print_warning "OBS: Omstart krävs för att I2C ska aktiveras helt"
}

# Skapa Python virtual environment
setup_python_venv() {
    print_header "Python Virtual Environment"
    
    PROJECT_DIR=${1:-.}
    USER=${SUDO_USER:-pi}
    
    print_info "Skapar Python virtual environment..."
    
    cd "$PROJECT_DIR" || {
        print_error "Kunde inte byta till projektmapp: $PROJECT_DIR"
        return 1
    }
    
    # Ta bort befintligt venv om det finns
    if [[ -d .venv ]]; then
        print_warning "Befintligt .venv hittades, tar bort..."
        rm -rf .venv
    fi
    
    # Skapa nytt venv
    sudo -u "$USER" python3 -m venv .venv || {
        print_error "Kunde inte skapa virtual environment"
        return 1
    }
    
    print_success "Virtual environment skapat"
    
    # Skapa requirements.txt om den saknas
    if [[ ! -f requirements.txt ]]; then
        print_info "Skapar requirements.txt för System 2.0..."
        cat > requirements.txt << 'EOF'
# Fotbollsplan Bevattning System 2.0 Dependencies
pymodbus>=3.0.0
requests>=2.28.0
python-dotenv>=0.21.0
fastapi>=0.95.0
uvicorn[standard]>=0.21.0
python-multipart>=0.0.5
smbus2>=0.4.0
passlib[bcrypt]>=1.7.4
dash>=2.0.0
plotly>=5.0.0
pandas>=1.3.0
httpx>=0.28.0
EOF
        chown "$USER:$USER" requirements.txt
        print_success "requirements.txt skapad"
    fi
    
    # Installera beroenden
    print_info "Installerar Python-beroenden (detta kan ta flera minuter)..."
    sudo -u "$USER" .venv/bin/pip install --upgrade pip
    sudo -u "$USER" .venv/bin/pip install -r requirements.txt || {
        print_error "Kunde inte installera Python-beroenden"
        return 1
    }
    
    # Installera från api_requirements.txt och display_requirements.txt om de finns
    if [[ -f api_requirements.txt ]]; then
        print_info "Installerar api_requirements.txt..."
        sudo -u "$USER" .venv/bin/pip install -r api_requirements.txt
    fi
    
    if [[ -f display_requirements.txt ]]; then
        print_info "Installerar display_requirements.txt..."
        sudo -u "$USER" .venv/bin/pip install -r display_requirements.txt
    fi
    
    print_success "Python-beroenden installerade"
}

# Konfigurera api_.env
configure_env() {
    print_header "api_.env Konfiguration"
    
    PROJECT_DIR=${1:-.}
    USER=${SUDO_USER:-pi}
    ENV_FILE="$PROJECT_DIR/api_.env"
    
    cd "$PROJECT_DIR" || return 1
    
    # Läs befintlig konfiguration om den finns
    if [[ -f "$ENV_FILE" ]]; then
        print_info "Befintlig api_.env hittades"
        read -p "Vill du skriva över den? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[YyJj]$ ]]; then
            print_info "Behåller befintlig konfiguration"
            return 0
        fi
    fi
    
    print_info "Konfigurerar miljövariabler..."
    echo
    
    # API_KEY
    read -p "API_KEY (för REST API-åtkomst) [byt-mig]: " API_KEY
    API_KEY=${API_KEY:-byt-mig}
    
    # Modbus
    echo
    print_info "Modbus PLC-konfiguration:"
    read -p "Modbus Host (PLC IP-adress) [$DEFAULT_MODBUS_HOST]: " MODBUS_HOST
    MODBUS_HOST=${MODBUS_HOST:-$DEFAULT_MODBUS_HOST}
    
    read -p "Modbus Port [$DEFAULT_MODBUS_PORT]: " MODBUS_PORT
    MODBUS_PORT=${MODBUS_PORT:-$DEFAULT_MODBUS_PORT}
    
    read -p "Modbus Unit ID [$DEFAULT_MODBUS_UNIT]: " MODBUS_UNIT
    MODBUS_UNIT=${MODBUS_UNIT:-$DEFAULT_MODBUS_UNIT}
    
    # GPS-koordinater
    echo
    print_info "GPS-koordinater (Håkanryd, Bromölla):"
    read -p "Latitude [$DEFAULT_LATITUDE]: " LATITUDE
    LATITUDE=${LATITUDE:-$DEFAULT_LATITUDE}
    
    read -p "Longitude [$DEFAULT_LONGITUDE]: " LONGITUDE
    LONGITUDE=${LONGITUDE:-$DEFAULT_LONGITUDE}
    
    # SMTP (valfritt)
    echo
    read -p "Vill du konfigurera SMTP för e-postnotifieringar? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[YyJj]$ ]]; then
        read -p "SMTP Server [$DEFAULT_SMTP_HOST]: " SMTP_HOST
        SMTP_HOST=${SMTP_HOST:-$DEFAULT_SMTP_HOST}
        
        read -p "SMTP Port [$DEFAULT_SMTP_PORT]: " SMTP_PORT
        SMTP_PORT=${SMTP_PORT:-$DEFAULT_SMTP_PORT}
        
        read -p "E-postadress (SMTP User): " SMTP_USER
        read -sp "E-postlösenord (SMTP Password): " SMTP_PASS
        echo
        
        read -p "Avsändare (From) [$SMTP_USER]: " SMTP_FROM
        SMTP_FROM=${SMTP_FROM:-$SMTP_USER}
        
        read -p "Mottagare (To, kommaseparerade) [$SMTP_USER]: " SMTP_TO
        SMTP_TO=${SMTP_TO:-$SMTP_USER}
    else
        SMTP_HOST="$DEFAULT_SMTP_HOST"
        SMTP_PORT="$DEFAULT_SMTP_PORT"
        SMTP_USER=""
        SMTP_PASS=""
        SMTP_FROM=""
        SMTP_TO=""
    fi
    
    # Skapa api_.env
    cat > "$ENV_FILE" << EOF
# Fotbollsplan-bevattning Environment Configuration
# Generated by setup.sh - $(date)

# API Configuration
API_KEY=$API_KEY
API_URL=http://127.0.0.1:8000

# Modbus Configuration
MODBUS_HOST=$MODBUS_HOST
MODBUS_PORT=$MODBUS_PORT
MODBUS_UNIT=$MODBUS_UNIT

# Weather Data Location (Håkanryd, Bromölla)
LATITUDE=$LATITUDE
LONGITUDE=$LONGITUDE

# I2C Configuration (System 2.0)
DISPLAY_1_I2C_ADDRESS=$DISPLAY_1_I2C_ADDRESS
I2C_BUTTON_ADDRESS=$I2C_BUTTON_ADDRESS

# SMTP Configuration
SMTP_HOST=$SMTP_HOST
SMTP_PORT=$SMTP_PORT
SMTP_USER=$SMTP_USER
SMTP_PASS=$SMTP_PASS
SMTP_FROM=$SMTP_FROM
SMTP_TO=$SMTP_TO
SMTP_TIMEOUT=10

# Healthcheck Configuration
HEALTHCHECK_TIMEOUT=5
HEALTHCHECK_RETRIES=3

# Dash Process View Configuration
DASH_HOST=0.0.0.0
DASH_PORT=8050
EOF
    
    # Sätt säkra rättigheter
    chown "$USER:$USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    
    print_success "api_.env konfigurerad"
    print_info "Fil: $ENV_FILE (rättigheter: 600)"
}

# Setup superadmin
setup_superadmin() {
    print_header "Superadmin Setup"
    
    PROJECT_DIR=${1:-.}
    USER=${SUDO_USER:-pi}
    
    cd "$PROJECT_DIR" || return 1
    
    # Aktivera venv och kör user_management.py
    if [[ ! -f user_management.py ]]; then
        print_warning "user_management.py hittades inte, hoppar över superadmin-setup"
        return 0
    fi
    
    print_info "Skapar superadmin-användare..."
    
    # Kör Python-script för att skapa superadmin
    sudo -u "$USER" .venv/bin/python3 << 'PYTHON_SCRIPT'
import sys
import getpass
from pathlib import Path

# Import user_management
try:
    from user_management import SuperAdminManager
except ImportError:
    print("user_management.py kunde inte importeras")
    sys.exit(1)

print("\nSuperadmin-användare krävs för att komma åt admin-funktioner.")
print("Lösenordet måste vara minst 8 tecken långt.\n")

while True:
    password = getpass.getpass("Ange superadmin-lösenord: ")
    password_confirm = getpass.getpass("Bekräfta lösenord: ")
    
    if password != password_confirm:
        print("Lösenorden matchar inte. Försök igen.\n")
        continue
    
    if len(password) < 8:
        print("Lösenordet måste vara minst 8 tecken långt. Försök igen.\n")
        continue
    
    break

try:
    manager = SuperAdminManager("superadmin.txt")
    manager.set_password(password)
    print("\n✓ Superadmin-användare skapad (superadmin.txt)")
except Exception as e:
    print(f"\n✗ Fel vid skapande av superadmin: {e}")
    sys.exit(1)
PYTHON_SCRIPT
    
    if [[ $? -eq 0 ]]; then
        # Sätt säkra rättigheter
        if [[ -f superadmin.txt ]]; then
            chown "$USER:$USER" superadmin.txt
            chmod 600 superadmin.txt
            print_success "Superadmin konfigurerad (rättigheter: 600)"
        fi
    else
        print_error "Superadmin-setup misslyckades"
        return 1
    fi
}

# Installera Tailscale
install_tailscale() {
    print_header "Tailscale Installation (Valfritt)"
    
    print_info "Tailscale ger säker fjärråtkomst utan portvidarebefordran"
    read -p "Vill du installera Tailscale? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[YyJj]$ ]] && [[ -n $REPLY ]]; then
        print_info "Hoppar över Tailscale-installation"
        return 0
    fi
    
    # Kontrollera om redan installerat
    if command -v tailscale &> /dev/null; then
        print_success "Tailscale är redan installerat"
        return 0
    fi
    
    print_info "Installerar Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh || {
        print_error "Tailscale-installation misslyckades"
        return 1
    }
    
    print_success "Tailscale installerat"
    
    print_info "Konfigurerar Tailscale..."
    print_warning "Du behöver autentisera via URL:en som visas"
    
    tailscale up --ssh || {
        print_warning "Tailscale-konfiguration misslyckades"
        return 1
    }
    
    print_success "Tailscale konfigurerat"
    
    # Visa status
    if tailscale status &> /dev/null; then
        echo
        print_info "Tailscale status:"
        tailscale status
    fi
}

# Installera systemd services
install_systemd_services() {
    print_header "systemd Services Installation"
    
    PROJECT_DIR=${1:-.}
    USER=${SUDO_USER:-pi}
    
    cd "$PROJECT_DIR" || return 1
    
    print_info "Installerar systemd services..."
    
    # Lista services att installera
    SERVICES=(
        "systemd_bevattning-api.service:bevattning-api.service"
        "systemd_display-manager.service:display-manager.service"
        "systemd_bevattning-controller.service:bevattning-controller.service"
        "systemd_bevattning-scheduler.service:bevattning-scheduler.service"
        "systemd_bevattning-scheduler.timer:bevattning-scheduler.timer"
        "systemd_unipi-modbus.service:unipi-modbus.service"
        "systemd_todo-checklist.service:todo-checklist.service"
        "systemd_di-monitor.service:di-monitor.service"
        "systemd_dashboard-hub.service:dashboard-hub.service"
        "systemd_user-management.service:user-management.service"
        "systemd_dash-process-view.service:dash-process-view.service"
    )
    
    # Installera varje service
    for SERVICE_PAIR in "${SERVICES[@]}"; do
        SRC="${SERVICE_PAIR%%:*}"
        DEST="${SERVICE_PAIR##*:}"
        
        if [[ ! -f "$SRC" ]]; then
            print_warning "$SRC hittades inte, hoppar över"
            continue
        fi
        
        # Läs service-fil och ersätt sökvägar
        sed -e "s|/home/pi/fotbollsplan-bevattning|$PROJECT_DIR|g" \
            -e "s|^User=.*|User=$USER|" \
            -e "s|^Group=.*|Group=$USER|" \
            "$SRC" > "/etc/systemd/system/$DEST"
        
        print_success "Installerade $DEST"
    done
    
    # Reload systemd
    systemctl daemon-reload || {
        print_error "systemctl daemon-reload misslyckades"
        return 1
    }
    
    # Aktivera services
    print_info "Aktiverar services..."
    
    # Grundläggande services
    systemctl enable bevattning-controller.service 2>/dev/null || print_warning "Kunde inte aktivera bevattning-controller"
    systemctl enable bevattning-api.service 2>/dev/null || print_warning "Kunde inte aktivera bevattning-api"
    systemctl enable display-manager.service 2>/dev/null || print_warning "Kunde inte aktivera display-manager"
    systemctl enable bevattning-scheduler.timer 2>/dev/null || print_warning "Kunde inte aktivera bevattning-scheduler.timer"
    systemctl enable unipi-modbus.service 2>/dev/null || print_warning "Kunde inte aktivera unipi-modbus"
    
    # Webbgränssnitt (System 2.0)
    systemctl enable dashboard-hub.service 2>/dev/null || print_warning "Kunde inte aktivera dashboard-hub"
    systemctl enable di-monitor.service 2>/dev/null || print_warning "Kunde inte aktivera di-monitor"
    systemctl enable user-management.service 2>/dev/null || print_warning "Kunde inte aktivera user-management"
    systemctl enable todo-checklist.service 2>/dev/null || print_warning "Kunde inte aktivera todo-checklist"
    systemctl enable dash-process-view.service 2>/dev/null || print_warning "Kunde inte aktivera dash-process-view"
    
    print_success "systemd services installerade och aktiverade"
    print_warning "Services startar automatiskt efter omstart"
}

# Kör post-installation verification
run_verification() {
    print_header "System Verification"
    
    PROJECT_DIR=${1:-.}
    
    if [[ -f "$PROJECT_DIR/verify.sh" ]]; then
        print_info "Kör verify.sh..."
        bash "$PROJECT_DIR/verify.sh" --skip-i2c || {
            print_warning "Verifiering hittade problem (se ovan)"
        }
    else
        print_warning "verify.sh hittades inte, hoppar över verifiering"
    fi
}

# Erbjud hardware-tester
offer_hardware_tests() {
    print_header "Hardware Tester"
    
    PROJECT_DIR=${1:-.}
    
    print_info "Hardware-tester är tillgängliga för att verifiera PLC-anslutning"
    echo
    echo "  relay_test.py   - Testa reläer och ingångar"
    echo "  email_test.py   - Testa e-postnotifieringar"
    echo
    print_info "Kör testerna efter omstart när I2C är aktiverat"
    print_info "Exempel: cd $PROJECT_DIR && source .venv/bin/activate && python3 relay_test.py --host <plc-ip>"
}

# Main installation flow
main() {
    print_header "Fotbollsplan Bevattning System 2.0 - Installation"
    
    echo "Detta script kommer att installera och konfigurera:"
    echo "  ✓ Systempaket (Python 3, I2C-verktyg, build-verktyg)"
    echo "  ✓ I2C för Display 1 och Arkadknappar"
    echo "  ✓ Python Virtual Environment"
    echo "  ✓ Python-beroenden (inkl. Flask, Dash, FastAPI)"
    echo "  ✓ api_.env konfiguration"
    echo "  ✓ Superadmin-användare"
    echo "  ✓ Tailscale (valfritt)"
    echo "  ✓ systemd services (11 tjänster)"
    echo "  ✓ 6 webbgränssnitt:"
    echo "     • Dashboard Hub (8090) - Startsida"
    echo "     • Bevattning API (8000) - Huvudstyrning"
    echo "     • DI Monitor (8081) - Knapp/Sensor-övervakning"
    echo "     • Användarhantering (8082) - Användaradmin"
    echo "     • Process View (8050) - Grafisk visualisering"
    echo "     • TODO Checklist (8080) - Projektlista"
    echo
    
    read -p "Vill du fortsätta? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[YyJj]$ ]] && [[ -n $REPLY ]]; then
        print_info "Installation avbruten"
        exit 0
    fi
    
    # Kontroller
    check_root
    check_raspberry_pi
    
    if ! check_internet; then
        print_warning "Ingen internet-anslutning detekterad"
        read -p "Vill du fortsätta ändå? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[YyJj]$ ]]; then
            exit 1
        fi
    fi
    
    # Hitta projektmapp
    PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    print_info "Projektmapp: $PROJECT_DIR"
    
    # Installation steps
    install_system_packages || exit 1
    enable_i2c || exit 1
    setup_python_venv "$PROJECT_DIR" || exit 1
    configure_env "$PROJECT_DIR" || exit 1
    setup_superadmin "$PROJECT_DIR" || exit 1
    install_tailscale
    install_systemd_services "$PROJECT_DIR" || exit 1
    run_verification "$PROJECT_DIR"
    offer_hardware_tests "$PROJECT_DIR"
    
    # Slutsammanfattning
    print_header "Installation Klar!"
    
    print_success "Fotbollsplan Bevattning System 2.0 har installerats!"
    echo
    print_info "📖 Fullständig dokumentation: ${GREEN}INSTALL_SYSTEM2.md${NC}"
    echo
    print_info "Nästa steg:"
    echo "  1. Starta om systemet för att aktivera I2C:"
    echo "     ${GREEN}sudo reboot${NC}"
    echo
    echo "  2. Efter omstart, verifiera I2C-enheter:"
    echo "     ${GREEN}i2cdetect -y 1${NC}"
    echo "     (Du ska se: 0x27 för Display 1, 0x20 för Arkadknappar)"
    echo
    echo "  3. Starta tjänsterna:"
    echo "     ${GREEN}sudo systemctl start unipi-modbus${NC}"
    echo "     ${GREEN}sudo systemctl start bevattning-controller${NC}"
    echo "     ${GREEN}sudo systemctl start bevattning-api${NC}"
    echo "     ${GREEN}sudo systemctl start display-manager${NC}"
    echo "     ${GREEN}sudo systemctl start dashboard-hub${NC}"
    echo "     ${GREEN}sudo systemctl start di-monitor${NC}"
    echo "     ${GREEN}sudo systemctl start user-management${NC}"
    echo
    echo
    echo "  4. Öppna webbgränssnitt:"
    IP=$(hostname -I | awk '{print $1}')
    echo "     ${GREEN}🏠 Dashboard Hub (STARTA HÄR): http://$IP:8090${NC}"
    echo "     ${BLUE}ℹ  Härifrån når du alla andra gränssnitt!${NC}"
    echo
    echo "  5. Kör hårdvarutester (valfritt):"
    echo "     ${GREEN}cd $PROJECT_DIR${NC}"
    echo "     ${GREEN}source .venv/bin/activate${NC}"
    echo "     ${GREEN}python3 relay_test.py --host <plc-ip>${NC}"
    echo "     ${GREEN}python3 email_test.py${NC}"
    echo
    echo "  ${BLUE}📚 Dokumentation:${NC}"
    echo "     README.md - Översikt och snabbstart"
    echo "     WEBBGRANSSNITT_GUIDE.md - Guide för alla webbgränssnitt"
    echo "     TAILSCALE_ACCESS.md - Fjärråtkomst"
    echo
    
    read -p "Vill du starta om nu? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_info "Startar om om 5 sekunder..."
        sleep 5
        reboot
    fi
}

# Kör main
main "$@"
