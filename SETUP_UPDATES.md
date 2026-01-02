# Setup.sh Uppdateringar - System 2.0 med Kernel-moduler

## Ändringar som behövs i setup.sh

### 1. Lägg till efter `check_internet()`:

```bash
# Installera UniPi kernel-moduler (KRITISKT för GPIO)
install_unipi_kernel_modules() {
    print_header "UniPi Kernel-Moduler"
    
    print_info "UniPi 1.1 kräver kernel-moduler för GPIO-funktionalitet"
    print_info "Utan dessa moduler kommer digitala ingångar (DI1-DI12) inte fungera!"
    
    if ! get_yes_no "Vill du installera UniPi kernel-moduler?" "true"; then
        print_warning "Hoppar över kernel-moduler - systemet kommer ha begränsad funktionalitet"
        return 0
    fi
    
    # Kontrollera om moduler redan är installerade
    if lsmod | grep -q "unipi"; then
        print_success "UniPi kernel-moduler redan installerade"
        return 0
    fi
    
    print_info "Installerar från repo.unipi.technology..."
    
    # Installera kernel-moduler
    wget -qO - https://repo.unipi.technology/debian/raspberry-unipi1.sh | bash || {
        print_error "Kunde inte installera UniPi kernel-moduler"
        print_info "Försök manuellt:"
        echo "  wget -qO - https://repo.unipi.technology/debian/raspberry-unipi1.sh | sudo bash"
        return 1
    }
    
    print_success "UniPi kernel-moduler installerade"
    print_warning "OBS: Systemet måste startas om för att moduler ska laddas!"
    REBOOT_REQUIRED=true
}

# Stoppa pigpiod som blockerar GPIO
disable_pigpiod() {
    print_header "GPIO Konflikt-Fix"
    
    if systemctl is-active --quiet pigpiod.service 2>/dev/null; then
        print_warning "pigpiod.service körs och blockerar GPIO-access"
        print_info "Detta måste stoppas för att RPi.GPIO ska fungera"
        
        if get_yes_no "Vill du stoppa och disabla pigpiod?" "true"; then
            systemctl stop pigpiod.service
            systemctl disable pigpiod.service
            print_success "pigpiod stoppad och disablad"
        else
            print_warning "pigpiod fortsätter köra - GPIO kommer INTE fungera!"
        fi
    else
        print_info "pigpiod körs inte - inget att göra"
    fi
}
```

### 2. Uppdatera `main()` funktionen:

```bash
main() {
    check_root
    print_banner
    
    # System checks
    check_raspberry_pi
    check_internet
    
    # Installation
    update_system
    install_dependencies
    install_unipi_kernel_modules    # NYTT: Kernel-moduler
    disable_pigpiod                 # NYTT: Fix GPIO-konflikt
    enable_i2c
    create_venv
    install_python_requirements
    create_directories
    setup_environment
    configure_smtp
    install_services
    
    # Final steps
    print_completion_message
}
```

### 3. Uppdatera `install_services()` för .venv:

Ersätt raden där service-filer kopieras med sed-kommando som fixar Python-sökvägar:

```bash
install_services() {
    print_header "Systemd Services"
    
    # ...befintlig kod...
    
    # Installera varje service
    for service in "${services[@]}"; do
        if [[ -f "$service" ]]; then
            service_name=$(basename "$service")
            print_info "Installerar $service_name..."
            
            # KRITISK FIX: Använd .venv Python istället för system Python
            sed -e "s|/home/pi/fotbollsplan-bevattning|$PROJECT_DIR|g" \
                -e "s|/usr/bin/python3.9|$PROJECT_DIR/.venv/bin/python3|g" \
                -e "s|/usr/bin/python3|$PROJECT_DIR/.venv/bin/python3|g" \
                -e "s|python3.9|$PROJECT_DIR/.venv/bin/python3|g" \
                -e "s|User=pi|User=$SUDO_USER|g" \
                -e "s|Group=pi|Group=$SUDO_USER|g" \
                "$service" > "/etc/systemd/system/$service_name"
            
            if [[ $? -eq 0 ]]; then
                print_success "$service_name installerad"
            else
                print_error "Kunde inte installera $service_name"
            fi
        fi
    done
    
    # ...befintlig kod...
}
```

### 4. Lägg till reboot-varning i slutet:

```bash
print_completion_message() {
    print_header "Installation Slutförd!"
    print_success "Systemet är nu installerat"
    
    echo ""
    echo "Nästa steg:"
    echo "1. Redigera api_.env med dina inställningar"
    echo "2. Konfigurera SMTP i superadmin.txt (om du vill ha e-postnotiser)"
    
    if [[ "$REBOOT_REQUIRED" == "true" ]]; then
        echo ""
        print_warning "⚠️  REBOOT KRÄVS för att ladda UniPi kernel-moduler!"
        echo ""
        echo "Efter reboot, starta tjänsterna:"
    else
        echo "3. Starta tjänsterna:"
    fi
    
    echo "   sudo systemctl start unipi-modbus"
    echo "   sudo systemctl start display-manager"
    echo "   sudo systemctl start bevattning-api"
    echo "   sudo systemctl start bevattning-controller"
    echo ""
    echo "4. Kontrollera status:"
    echo "   sudo systemctl status unipi-modbus"
    echo "   lsmod | grep unipi  # Verifiera kernel-moduler"
    echo ""
    echo "5. Testa systemet:"
    echo "   cd $PROJECT_DIR"
    echo "   source .venv/bin/activate"
    echo "   python3 test_relays_safe.py  # Testa reläer"
    echo "   python3 test_di_monitor.py   # Testa digitala ingångar"
    echo ""
    
    if [[ "$REBOOT_REQUIRED" == "true" ]]; then
        echo ""
        print_warning "================================================"
        print_warning "  STARTA OM SYSTEMET NU MED: sudo reboot"
        print_warning "================================================"
        echo ""
    fi
}
```

---

## Ändringar som behövs i bevattning_controller.py

### Fixa hårdkodad API_URL (rad ~30):

```python
import os
from dotenv import load_dotenv

# Ladda .env-filen
load_dotenv("api_.env")

# API och Modbus-konfiguration
API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')
API_KEY = os.getenv('API_KEY', '')
DEFAULT_MODBUS_HOST = os.getenv('MODBUS_HOST', '127.0.0.1')
DEFAULT_MODBUS_PORT = int(os.getenv('MODBUS_PORT', '502'))
```

---

## Ändringar som behövs i display_manager.py

### Lägg till i början av filen:

```python
import os
from dotenv import load_dotenv

# Ladda environment-variabler
load_dotenv("api_.env")

# Configuration from environment
MODBUS_HOST = os.getenv('MODBUS_HOST', '127.0.0.1')
MODBUS_PORT = int(os.getenv('MODBUS_PORT', '502'))
```

### Uppdatera ModbusReader.__init__():

```python
class ModbusReader:
    """Helper for reading/writing Modbus registers"""
    
    def __init__(self, host: str = None, port: int = None, unit: int = 1, cache_duration: float = 0.5):
        # Use environment variables if not specified
        if host is None:
            host = MODBUS_HOST
        if port is None:
            port = MODBUS_PORT
            
        self.host = host
        self.port = port
        # ...rest av kod...
```

---

## Fil-städning (kör efter uppdateringar)

### Radera obsoleta filer:

```bash
cd /home/kamp/fotbollsplan-bevattning

# Gamla installationsscript
rm -f install.py
rm -f test_install_complete.py
rm -f test_setup.py

# Gamla UI-versioner
rm -f dash_app.py

# Obsoleta test-filer
rm -f api_relay_test.py
rm -f relay_test.py
```

### Flytta till archive:

```bash
mkdir -p archive/old_scripts_2026
mkdir -p archive/old_documentation_2026

# Dokumentation (ersatt av INSTALL_SYSTEM2.md & CHECKOUT_RAPPORT)
mv INSTALLATION.md archive/old_documentation_2026/ 2>/dev/null || true
```

---

## Sammanfattning

**KRITISKA ÄNDRINGAR:**
1. ✅ UniPi kernel-moduler installation
2. ✅ pigpiod disable (GPIO-konflikt)
3. ✅ .venv Python i systemd-tjänster
4. ✅ Environment-variabler i bevattning_controller.py
5. ✅ Environment-variabler i display_manager.py

**RESULTAT:**
- Systemet kommer fungera direkt efter installation + reboot
- Alla DI (digitala ingångar) kommer läsas korrekt
- NC-kontakter (DI3, DI10, DI11, DI12) inverterade automatiskt
- Ingen hårdkodade sökvägar eller portar

**TEST EFTER INSTALLATION:**
```bash
# Efter reboot
lsmod | grep unipi                    # Ska visa rtc_unipi, unipi_id
systemctl status unipi-modbus         # Ska vara active
python3 test_di_monitor.py            # Ska visa DI3=HIGH, DI11=HIGH
```
