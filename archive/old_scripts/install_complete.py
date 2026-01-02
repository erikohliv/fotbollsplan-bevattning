#!/usr/bin/env python3
"""
Complete installation script for fotbollsplan-bevattning on Raspberry Pi 4 
running Debian Bookworm Lite.

This script performs a complete system setup including:
1. WiFi network scanning and configuration
2. System package installation (apt)
3. Python virtual environment setup
4. Environment configuration (API_KEY, Modbus, SMTP)
5. Tailscale installation and configuration (optional)
6. I2C and display configuration
7. systemd services installation and activation
8. Security settings and permissions

Usage:
    sudo python3 install_complete.py

Note: This script requires root privileges for system configuration.
"""

import os
import sys
import subprocess
import re
import time
import shutil
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from getpass import getpass

# Constants
DEFAULT_API_KEY = 'byt-mig'
DEFAULT_MODBUS_HOST = '127.0.0.1'
DEFAULT_MODBUS_PORT = '502'
DEFAULT_MODBUS_UNIT = '1'
DEFAULT_SMTP_HOST = 'smtp.gmail.com'
DEFAULT_SMTP_PORT = '587'
DEFAULT_SMTP_TIMEOUT = '10'
DEFAULT_HEALTHCHECK_TIMEOUT = '5'
DEFAULT_HEALTHCHECK_RETRIES = '3'
DEFAULT_USER = 'pi'
# System 2.0 - Håkanryd, Bromölla coordinates
DEFAULT_LATITUDE = '56.05'
DEFAULT_LONGITUDE = '14.40'
# System 2.0 - I2C addresses
DISPLAY_1_I2C_ADDRESS = '0x27'
I2C_BUTTON_ADDRESS = '0x20'

# System packages required for the project
REQUIRED_PACKAGES = [
    'python3',
    'python3-pip',
    'python3-venv',
    'python3-dev',
    'python3-smbus',
    'i2c-tools',
    'git',
    'curl',
    'wireless-tools',
    'wpasupplicant',
    'network-manager',
    'build-essential',
]


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"✓ {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"✗ {text}", file=sys.stderr)


def print_info(text: str) -> None:
    """Print an informational message."""
    print(f"ℹ {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"⚠ {text}")


def get_input(prompt: str, default: str = None, validator=None) -> str:
    """Get user input with optional default and validation."""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                user_input = default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if not user_input:
            print_error("Input cannot be empty. Please try again.")
            continue
        
        if validator:
            result = validator(user_input)
            # Handle both bool and tuple returns
            if isinstance(result, tuple):
                valid, _ = result
                if valid:
                    return user_input
            elif result:
                return user_input
            
            print_error("Invalid input. Please try again.")
            continue
        
        return user_input


def get_yes_no(prompt: str, default: bool = False) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes', 'j', 'ja']:
            return True
        if response in ['n', 'no', 'nej']:
            return False
        print_error("Please answer 'y' or 'n'.")


def run_command(cmd: List[str], timeout: int = 60, check: bool = True) -> Tuple[bool, str, str]:
    """
    Run a command and return success status, stdout, and stderr.
    
    Args:
        cmd: Command and arguments as list
        timeout: Command timeout in seconds
        check: If True, raise exception on non-zero exit
    
    Returns:
        (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", f"Command timed out after {timeout}s")
    except subprocess.CalledProcessError as e:
        return (False, e.stdout or "", e.stderr or "")
    except Exception as e:
        return (False, "", str(e))


def validate_ipv4(ip: str) -> bool:
    """Validate IPv4 address format."""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    
    octets = ip.split('.')
    for octet in octets:
        try:
            if not 0 <= int(octet) <= 255:
                return False
        except ValueError:
            return False
    
    return True


def validate_port(port_str: str) -> Tuple[bool, int]:
    """Validate port number (1-65535)."""
    try:
        port = int(port_str)
        if 1 <= port <= 65535:
            return True, port
        return False, 0
    except ValueError:
        return False, 0


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# ============================================================================
# WiFi Configuration Functions
# ============================================================================

def get_wireless_interface() -> Optional[str]:
    """
    Find the wireless network interface.
    
    Returns:
        Wireless interface name (e.g., 'wlan0') or None if not found
    """
    success, stdout, _ = run_command(['ls', '/sys/class/net'], check=False)
    if not success:
        return None
    
    interfaces = stdout.strip().split('\n')
    for iface in interfaces:
        if iface.startswith('wlan') or iface.startswith('wlp'):
            return iface
    
    return None


def is_wifi_connected() -> bool:
    """
    Check if WiFi is currently connected.
    
    Returns:
        True if connected to WiFi with IP address, False otherwise
    """
    success, stdout, _ = run_command(['ip', 'addr', 'show'], check=False)
    if not success:
        return False
    
    lines = stdout.split('\n')
    for i, line in enumerate(lines):
        if ('wlan' in line or 'wlp' in line) and 'state UP' in line:
            # Check following lines for inet address
            for j in range(i, min(i+10, len(lines))):
                if 'inet ' in lines[j] and '127.0.0.1' not in lines[j]:
                    return True
    
    return False


def scan_wifi_networks() -> List[Dict[str, str]]:
    """
    Scan for available WiFi networks.
    
    Returns:
        List of dictionaries with network information (SSID, signal, security)
    """
    print_info("Scanning for WiFi networks...")
    
    # Find wireless interface
    wlan_interface = get_wireless_interface()
    
    if not wlan_interface:
        print_error("No wireless interface found")
        return []
    
    print_info(f"Using wireless interface: {wlan_interface}")
    
    # Bring interface up if needed
    run_command(['ip', 'link', 'set', wlan_interface, 'up'], check=False)
    time.sleep(2)
    
    # Scan for networks using iw or nmcli
    networks = []
    
    # Try nmcli first (NetworkManager)
    success, stdout, _ = run_command(
        ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list'],
        check=False,
        timeout=30
    )
    
    if success and stdout:
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(':')
            if len(parts) >= 2:
                ssid = parts[0].strip()
                signal = parts[1].strip() if len(parts) > 1 else '0'
                security = parts[2].strip() if len(parts) > 2 else 'Open'
                
                if ssid and ssid != '--':  # Skip empty or hidden SSIDs
                    networks.append({
                        'ssid': ssid,
                        'signal': signal,
                        'security': security
                    })
    else:
        # Fallback to iw scan
        success, stdout, _ = run_command(
            ['iw', 'dev', wlan_interface, 'scan'],
            check=False,
            timeout=30
        )
        
        if success and stdout:
            current_ssid = None
            current_signal = '0'
            current_security = 'Open'
            
            for line in stdout.split('\n'):
                line = line.strip()
                if line.startswith('SSID:'):
                    if current_ssid:
                        networks.append({
                            'ssid': current_ssid,
                            'signal': current_signal,
                            'security': current_security
                        })
                    current_ssid = line.split(':', 1)[1].strip()
                    current_security = 'Open'
                elif 'signal:' in line.lower():
                    match = re.search(r'(-?\d+\.?\d*)', line)
                    if match:
                        current_signal = match.group(1)
                elif 'WPA' in line or 'RSN' in line:
                    current_security = 'WPA/WPA2'
            
            if current_ssid:
                networks.append({
                    'ssid': current_ssid,
                    'signal': current_signal,
                    'security': current_security
                })
    
    # Remove duplicates and sort by signal strength
    seen = set()
    unique_networks = []
    for net in networks:
        if net['ssid'] not in seen:
            seen.add(net['ssid'])
            unique_networks.append(net)
    
    # Sort by signal strength (descending)
    try:
        unique_networks.sort(key=lambda x: float(x['signal']), reverse=True)
    except ValueError:
        pass  # Keep original order if signal is not numeric
    
    return unique_networks


def configure_wifi(ssid: str, password: str) -> bool:
    """
    Configure WiFi connection using NetworkManager.
    
    Args:
        ssid: Network SSID
        password: Network password
    
    Returns:
        True if configuration successful, False otherwise
    """
    print_info(f"Configuring WiFi connection to '{ssid}'...")
    
    # Try using nmcli (NetworkManager)
    success, stdout, stderr = run_command(
        ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password],
        check=False,
        timeout=30
    )
    
    if success:
        print_success(f"Successfully connected to '{ssid}'")
        return True
    
    print_warning("NetworkManager connection failed, trying wpa_supplicant...")
    
    # Fallback to wpa_supplicant configuration
    # Use wpa_passphrase for secure password handling
    try:
        # Generate proper PSK using wpa_passphrase
        result = subprocess.run(
            ['wpa_passphrase', ssid, password],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print_error("Failed to generate wpa_supplicant configuration")
            return False
        
        # Extract the generated configuration (wpa_passphrase output)
        wpa_config = result.stdout
        
    except FileNotFoundError:
        # wpa_passphrase not available, manual config with escaping
        print_warning("wpa_passphrase not found, using manual configuration")
        # Escape special characters in password for shell safety
        # Replace: backslash, double quote, single quote, backtick, dollar sign
        escaped_password = (password
                          .replace('\\', '\\\\')
                          .replace('"', '\\"')
                          .replace("'", "\\'")
                          .replace('`', '\\`')
                          .replace('$', '\\$'))
        wpa_config = f"""
network={{
    ssid="{ssid}"
    psk="{escaped_password}"
    key_mgmt=WPA-PSK
}}
"""
    except Exception as e:
        print_error(f"Failed to generate WiFi configuration: {e}")
        return False
    
    wpa_conf_path = '/etc/wpa_supplicant/wpa_supplicant.conf'
    
    try:
        # Backup existing config
        if os.path.exists(wpa_conf_path):
            shutil.copy(wpa_conf_path, wpa_conf_path + '.backup')
        
        # Append to config
        with open(wpa_conf_path, 'a') as f:
            f.write(wpa_config)
        
        # Restart networking
        run_command(['systemctl', 'restart', 'networking'], check=False, timeout=20)
        time.sleep(5)
        
        # Check if connected using helper function
        if is_wifi_connected():
            print_success(f"Successfully configured WiFi for '{ssid}'")
            return True
        
    except Exception as e:
        print_error(f"Failed to configure WiFi: {e}")
        # Restore backup if exists
        if os.path.exists(wpa_conf_path + '.backup'):
            shutil.copy(wpa_conf_path + '.backup', wpa_conf_path)
    
    return False


def setup_wifi() -> bool:
    """
    Interactive WiFi setup with network scanning.
    
    Returns:
        True if WiFi configured successfully or skipped, False on error
    """
    print_header("WiFi Network Configuration")
    
    # Check if already connected to WiFi using helper function
    if is_wifi_connected():
        print_success("Already connected to WiFi")
        if not get_yes_no("Do you want to configure a different network?", default=False):
            return True
    
    # Scan for networks
    networks = scan_wifi_networks()
    
    if not networks:
        print_warning("No WiFi networks found")
        if not get_yes_no("Do you want to manually enter network details?", default=True):
            return True  # Skip WiFi setup
    else:
        print_info(f"Found {len(networks)} WiFi network(s):\n")
        for i, net in enumerate(networks[:20], 1):  # Show max 20 networks
            security_icon = "🔒" if net['security'] != 'Open' else "🔓"
            print(f"  {i:2d}. {security_icon} {net['ssid']:<30} Signal: {net['signal']:>4}%")
        
        print("\n  0. Enter network manually")
        print(f"  {len(networks)+1}. Skip WiFi configuration")
        
        while True:
            try:
                choice = input(f"\nSelect network (0-{len(networks)+1}): ").strip()
                if not choice:
                    continue
                choice_num = int(choice)
                
                if choice_num == len(networks) + 1:
                    print_info("Skipping WiFi configuration")
                    return True
                elif choice_num == 0:
                    break  # Manual entry
                elif 1 <= choice_num <= len(networks):
                    selected_network = networks[choice_num - 1]
                    ssid = selected_network['ssid']
                    
                    if selected_network['security'] == 'Open':
                        if get_yes_no(f"Connect to open network '{ssid}'?", default=True):
                            return configure_wifi(ssid, "")
                    else:
                        print_info(f"Selected: {ssid}")
                        password = getpass("Enter WiFi password: ")
                        if password:
                            return configure_wifi(ssid, password)
                        else:
                            print_error("Password cannot be empty")
                            continue
                else:
                    print_error("Invalid choice")
            except ValueError:
                print_error("Please enter a number")
            except KeyboardInterrupt:
                print("\n")
                return False
    
    # Manual entry
    print_info("Manual WiFi configuration")
    ssid = input("Enter SSID (network name): ").strip()
    if not ssid:
        print_error("SSID cannot be empty")
        return False
    
    password = getpass("Enter WiFi password (leave empty for open network): ").strip()
    
    return configure_wifi(ssid, password)


# ============================================================================
# System Package Installation
# ============================================================================

def update_apt_cache() -> bool:
    """Update apt package cache."""
    print_info("Updating package cache...")
    success, _, stderr = run_command(['apt', 'update'], timeout=120)
    if success:
        print_success("Package cache updated")
        return True
    else:
        print_error(f"Failed to update package cache: {stderr}")
        return False


def install_system_packages() -> bool:
    """Install required system packages."""
    print_header("System Package Installation")
    
    print_info("Installing required packages:")
    for pkg in REQUIRED_PACKAGES:
        print(f"  • {pkg}")
    print()
    
    if not get_yes_no("Proceed with package installation?", default=True):
        print_info("Skipping package installation")
        return True
    
    # Update cache
    if not update_apt_cache():
        if not get_yes_no("Continue anyway?", default=False):
            return False
    
    # Install packages
    print_info("Installing packages (this may take several minutes)...")
    cmd = ['apt', 'install', '-y'] + REQUIRED_PACKAGES
    success, stdout, stderr = run_command(cmd, timeout=600)
    
    if success:
        print_success("All packages installed successfully")
        return True
    else:
        print_error(f"Package installation failed: {stderr}")
        return False


# ============================================================================
# I2C Configuration
# ============================================================================

def enable_i2c() -> bool:
    """Enable I2C interface for display communication."""
    print_header("I2C Interface Configuration")
    
    print_info("I2C is required for LCD display communication")
    
    if not get_yes_no("Do you want to enable I2C?", default=True):
        print_info("Skipping I2C configuration")
        return True
    
    # Check if raspi-config is available
    success, _, _ = run_command(['which', 'raspi-config'], check=False)
    
    if success:
        # Use raspi-config to enable I2C
        print_info("Enabling I2C using raspi-config...")
        success, _, stderr = run_command(
            ['raspi-config', 'nonint', 'do_i2c', '0'],
            check=False
        )
        if success:
            print_success("I2C enabled successfully")
        else:
            print_warning(f"raspi-config failed: {stderr}")
    
    # Also ensure i2c-dev module is loaded
    print_info("Ensuring i2c-dev module is loaded...")
    
    # Add to /etc/modules if not present
    modules_file = Path('/etc/modules')
    try:
        content = modules_file.read_text() if modules_file.exists() else ""
        if 'i2c-dev' not in content:
            with open(modules_file, 'a') as f:
                f.write('\ni2c-dev\n')
            print_success("Added i2c-dev to /etc/modules")
        
        # Load module now
        run_command(['modprobe', 'i2c-dev'], check=False)
        
    except Exception as e:
        print_error(f"Failed to configure i2c-dev module: {e}")
    
    # Add user to i2c group
    user = os.getenv('SUDO_USER', DEFAULT_USER)
    print_info(f"Adding user '{user}' to i2c group...")
    success, _, _ = run_command(['usermod', '-a', '-G', 'i2c', user], check=False)
    if success:
        print_success(f"User '{user}' added to i2c group")
    
    return True


# ============================================================================
# Python Environment Setup
# ============================================================================

def setup_python_environment(project_dir: Path, user: str) -> bool:
    """
    Set up Python virtual environment and install dependencies.
    
    Args:
        project_dir: Project directory path
        user: User who will own the virtual environment
    
    Returns:
        True if successful, False otherwise
    """
    print_header("Python Environment Setup")
    
    venv_dir = project_dir / '.venv'
    
    # Create virtual environment
    if venv_dir.exists():
        print_info("Virtual environment already exists")
        if not get_yes_no("Recreate virtual environment?", default=False):
            return True
        
        print_info("Removing existing virtual environment...")
        shutil.rmtree(venv_dir)
    
    print_info("Creating virtual environment...")
    success, _, stderr = run_command(
        ['python3', '-m', 'venv', str(venv_dir)],
        timeout=120
    )
    
    if not success:
        print_error(f"Failed to create virtual environment: {stderr}")
        return False
    
    print_success("Virtual environment created")
    
    # Create requirements.txt for System 2.0 if it doesn't exist
    req_file = project_dir / 'requirements.txt'
    if not req_file.exists():
        print_info("Creating requirements.txt for System 2.0...")
        requirements_content = """# Fotbollsplan Bevattning System 2.0 Dependencies
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
"""
        req_file.write_text(requirements_content)
        run_command(['chown', f'{user}:{user}', str(req_file)], check=False)
        print_success("requirements.txt created")
    
    # Install requirements
    pip_path = venv_dir / 'bin' / 'pip'
    
    # Upgrade pip first
    print_info("Upgrading pip...")
    run_command([str(pip_path), 'install', '--upgrade', 'pip'], timeout=120, check=False)
    
    for req_file in ['requirements.txt', 'api_requirements.txt', 'display_requirements.txt']:
        req_path = project_dir / req_file
        if not req_path.exists():
            print_warning(f"{req_file} not found, skipping")
            continue
        
        print_info(f"Installing dependencies from {req_file}...")
        success, _, stderr = run_command(
            [str(pip_path), 'install', '-r', str(req_path)],
            timeout=600
        )
        
        if success:
            print_success(f"Dependencies from {req_file} installed")
        else:
            print_error(f"Failed to install {req_file}: {stderr}")
            if not get_yes_no("Continue anyway?", default=True):
                return False
    
    # Set ownership
    print_info(f"Setting ownership to {user}...")
    run_command(['chown', '-R', f'{user}:{user}', str(venv_dir)], check=False)
    
    return True


# ============================================================================
# Environment Configuration
# ============================================================================

def configure_environment(project_dir: Path, user: str) -> bool:
    """
    Configure environment variables in api_.env file.
    
    Args:
        project_dir: Project directory path
        user: User who will own the configuration file
    
    Returns:
        True if successful, False otherwise
    """
    print_header("Environment Configuration")
    
    env_file = project_dir / 'api_.env'
    env_vars = {}
    
    # Load existing configuration if present
    if env_file.exists():
        print_info(f"Found existing configuration: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # API Key
    default_key = env_vars.get('API_KEY', DEFAULT_API_KEY)
    api_key = get_input("API Key (för REST API-åtkomst)", default=default_key)
    env_vars['API_KEY'] = api_key
    
    # Modbus configuration
    print_info("\nModbus PLC-konfiguration:")
    default_host = env_vars.get('MODBUS_HOST', DEFAULT_MODBUS_HOST)
    modbus_host = get_input("Modbus Host (PLC IP-adress)", 
                           default=default_host, validator=validate_ipv4)
    env_vars['MODBUS_HOST'] = modbus_host
    
    default_port = env_vars.get('MODBUS_PORT', DEFAULT_MODBUS_PORT)
    modbus_port = get_input("Modbus Port", default=default_port, 
                           validator=validate_port)
    env_vars['MODBUS_PORT'] = modbus_port
    
    default_unit = env_vars.get('MODBUS_UNIT', DEFAULT_MODBUS_UNIT)
    while True:
        modbus_unit = get_input("Modbus Unit ID", default=default_unit)
        try:
            unit = int(modbus_unit)
            if 1 <= unit <= 255:
                env_vars['MODBUS_UNIT'] = modbus_unit
                break
            print_error("Unit ID must be between 1 and 255")
        except ValueError:
            print_error("Please enter a valid number")
    
    # Weather coordinates (System 2.0 - Håkanryd, Bromölla)
    print_info("\nGPS-koordinater för väderdata (Håkanryd, Bromölla):")
    default_lat = env_vars.get('LATITUDE', DEFAULT_LATITUDE)
    latitude = get_input("Latitude", default=default_lat)
    env_vars['LATITUDE'] = latitude
    
    default_lon = env_vars.get('LONGITUDE', DEFAULT_LONGITUDE)
    longitude = get_input("Longitude", default=default_lon)
    env_vars['LONGITUDE'] = longitude
    
    # I2C addresses (System 2.0)
    env_vars['DISPLAY_1_I2C_ADDRESS'] = DISPLAY_1_I2C_ADDRESS
    env_vars['I2C_BUTTON_ADDRESS'] = I2C_BUTTON_ADDRESS
    
    # SMTP configuration (optional)
    print_info("\nSMTP E-postkonfiguration (valfritt, för healthcheck-notifieringar):")
    if get_yes_no("Vill du konfigurera SMTP för e-postmeddelanden?", default=False):
        default_smtp_host = env_vars.get('SMTP_HOST', DEFAULT_SMTP_HOST)
        smtp_host = get_input("SMTP Server", default=default_smtp_host)
        env_vars['SMTP_HOST'] = smtp_host
        
        default_smtp_port = env_vars.get('SMTP_PORT', DEFAULT_SMTP_PORT)
        smtp_port = get_input("SMTP Port", default=default_smtp_port, validator=validate_port)
        env_vars['SMTP_PORT'] = smtp_port
        
        smtp_user = get_input("E-postadress (SMTP User)", validator=validate_email)
        env_vars['SMTP_USER'] = smtp_user
        
        smtp_pass = getpass("E-postlösenord (SMTP Password): ")
        env_vars['SMTP_PASS'] = smtp_pass
        
        default_from = env_vars.get('SMTP_FROM', smtp_user)
        smtp_from = get_input("Avsändare (From)", default=default_from, validator=validate_email)
        env_vars['SMTP_FROM'] = smtp_from
        
        default_to = env_vars.get('SMTP_TO', smtp_user)
        smtp_to = get_input("Mottagare (To, kommaseparerade)", default=default_to)
        env_vars['SMTP_TO'] = smtp_to
        
        env_vars['SMTP_TIMEOUT'] = DEFAULT_SMTP_TIMEOUT
    else:
        # Set defaults without prompting
        env_vars.setdefault('SMTP_HOST', DEFAULT_SMTP_HOST)
        env_vars.setdefault('SMTP_PORT', DEFAULT_SMTP_PORT)
        env_vars.setdefault('SMTP_TIMEOUT', DEFAULT_SMTP_TIMEOUT)
    
    # Set healthcheck defaults
    env_vars.setdefault('HEALTHCHECK_TIMEOUT', DEFAULT_HEALTHCHECK_TIMEOUT)
    env_vars.setdefault('HEALTHCHECK_RETRIES', DEFAULT_HEALTHCHECK_RETRIES)
    
    # Save configuration
    try:
        with open(env_file, 'w') as f:
            f.write("# Fotbollsplan-bevattning Environment Configuration\n")
            f.write("# Generated by install_complete.py (System 2.0)\n\n")
            
            f.write("# API Configuration\n")
            for key in ['API_KEY', 'API_URL']:
                if key in env_vars:
                    f.write(f"{key}={env_vars[key]}\n")
            # Add API_URL default if not present
            if 'API_URL' not in env_vars:
                f.write("API_URL=http://127.0.0.1:8000\n")
            
            f.write("\n# Modbus Configuration\n")
            for key in ['MODBUS_HOST', 'MODBUS_PORT', 'MODBUS_UNIT']:
                if key in env_vars:
                    f.write(f"{key}={env_vars[key]}\n")
            
            f.write("\n# Weather Data Location (Håkanryd, Bromölla)\n")
            for key in ['LATITUDE', 'LONGITUDE']:
                if key in env_vars:
                    f.write(f"{key}={env_vars[key]}\n")
            
            f.write("\n# I2C Configuration (System 2.0)\n")
            for key in ['DISPLAY_1_I2C_ADDRESS', 'I2C_BUTTON_ADDRESS']:
                if key in env_vars:
                    f.write(f"{key}={env_vars[key]}\n")
            
            f.write("\n# SMTP Configuration\n")
            smtp_keys = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 
                        'SMTP_FROM', 'SMTP_TO', 'SMTP_TIMEOUT']
            for key in smtp_keys:
                if key in env_vars:
                    f.write(f"{key}={env_vars[key]}\n")
            
            f.write("\n# Healthcheck Configuration\n")
            for key in ['HEALTHCHECK_TIMEOUT', 'HEALTHCHECK_RETRIES']:
                if key in env_vars:
                    f.write(f"{key}={env_vars[key]}\n")
            
            f.write("\n# Dash Process View Configuration\n")
            f.write("DASH_HOST=0.0.0.0\n")
            f.write("DASH_PORT=8050\n")
        
        # Set ownership
        run_command(['chown', f'{user}:{user}', str(env_file)], check=False)
        run_command(['chmod', '600', str(env_file)], check=False)  # Secure permissions
        
        print_success(f"Configuration saved to: {env_file}")
        return True
        
    except Exception as e:
        print_error(f"Failed to save configuration: {e}")
        return False


# ============================================================================
# Tailscale Setup
# ============================================================================

def setup_tailscale() -> bool:
    """Install and configure Tailscale for remote access."""
    print_header("Tailscale VPN Configuration")
    
    print_info("Tailscale ger säker fjärråtkomst utan portvidarebefordran")
    
    if not get_yes_no("Vill du installera Tailscale?", default=True):
        print_info("Skipping Tailscale installation")
        return True
    
    # Check if already installed
    success, _, _ = run_command(['which', 'tailscale'], check=False)
    
    if success:
        print_success("Tailscale is already installed")
        if not get_yes_no("Reconfigure Tailscale?", default=False):
            return True
    else:
        # Install Tailscale
        print_info("Installing Tailscale...")
        print_warning("This will download and execute the official Tailscale installation script")
        print_info("Script source: https://tailscale.com/install.sh")
        
        if not get_yes_no("Download and verify Tailscale installation script?", default=True):
            print_info("Tailscale installation cancelled")
            return True
        
        # Download script first
        print_info("Downloading installation script...")
        success, script_content, stderr = run_command(
            ['curl', '-fsSL', 'https://tailscale.com/install.sh'],
            timeout=60
        )
        
        if not success:
            print_error(f"Failed to download Tailscale script: {stderr}")
            return False
        
        # Save to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Show script size and first lines for verification
            print_info(f"Script downloaded ({len(script_content)} bytes)")
            print_info("First lines of script:")
            for line in script_content.split('\n')[:5]:
                if line.strip():
                    print(f"  {line}")
            
            if not get_yes_no("Execute this script to install Tailscale?", default=True):
                os.unlink(script_path)
                print_info("Tailscale installation cancelled")
                return True
            
            # Execute the script
            print_info("Installing Tailscale...")
            success, _, stderr = run_command(
                ['sh', script_path],
                timeout=180
            )
            
            # Clean up
            os.unlink(script_path)
            
            if not success:
                print_error(f"Failed to install Tailscale: {stderr}")
                return False
            
            print_success("Tailscale installed successfully")
        
        except Exception as e:
            if os.path.exists(script_path):
                os.unlink(script_path)
            print_error(f"Error during Tailscale installation: {e}")
            return False
    
    # Configure Tailscale
    print_info("Configuring Tailscale with SSH enabled...")
    print_info("You will need to authenticate via the URL shown below")
    
    success, stdout, stderr = run_command(
        ['tailscale', 'up', '--ssh'],
        timeout=120,
        check=False
    )
    
    if success or 'already logged in' in stderr.lower():
        print_success("Tailscale configured")
        if stdout:
            print(stdout)
    else:
        print_error(f"Failed to configure Tailscale: {stderr}")
        return False
    
    # Show status
    success, stdout, _ = run_command(['tailscale', 'status'], check=False)
    if success and stdout:
        print_info("Tailscale status:")
        print(stdout)
    
    return True


# ============================================================================
# Superadmin Setup (System 2.0)
# ============================================================================

def setup_superadmin(project_dir: Path, user: str) -> bool:
    """
    Set up superadmin user with bcrypt password hashing.
    
    Args:
        project_dir: Project directory path
        user: User who will own the superadmin.txt file
    
    Returns:
        True if successful, False otherwise
    """
    print_header("Superadmin Setup (System 2.0)")
    
    # Check if user_management.py exists
    user_mgmt_path = project_dir / 'user_management.py'
    if not user_mgmt_path.exists():
        print_warning("user_management.py not found, skipping superadmin setup")
        return True
    
    print_info("Creating superadmin user for admin access...")
    print_info("Password must be at least 8 characters long")
    print()
    
    # Create Python script to run in venv
    setup_script = project_dir / '.setup_superadmin_temp.py'
    try:
        setup_script.write_text("""
import sys
import getpass
from pathlib import Path

try:
    from user_management import SuperAdminManager
except ImportError:
    print("ERROR: Could not import user_management")
    sys.exit(1)

print("Superadmin user is required for admin access.")
print("Password must be at least 8 characters long.\\n")

while True:
    password = getpass.getpass("Enter superadmin password: ")
    password_confirm = getpass.getpass("Confirm password: ")
    
    if password != password_confirm:
        print("Passwords do not match. Try again.\\n")
        continue
    
    if len(password) < 8:
        print("Password must be at least 8 characters long. Try again.\\n")
        continue
    
    break

try:
    manager = SuperAdminManager("superadmin.txt")
    manager.set_password(password)
    print("\\n✓ Superadmin user created (superadmin.txt)")
except Exception as e:
    print(f"\\n✗ Error creating superadmin: {e}")
    sys.exit(1)
""")
        
        # Run the script as the user
        venv_python = project_dir / '.venv' / 'bin' / 'python3'
        
        if not venv_python.exists():
            print_error("Virtual environment not found")
            return False
        
        # Run as user using sudo -u
        success, _, stderr = run_command(
            ['sudo', '-u', user, str(venv_python), str(setup_script)],
            timeout=120,
            check=False
        )
        
        # Clean up temp script
        setup_script.unlink()
        
        if not success:
            print_error(f"Failed to create superadmin: {stderr}")
            return False
        
        # Set secure permissions on superadmin.txt
        superadmin_file = project_dir / 'superadmin.txt'
        if superadmin_file.exists():
            run_command(['chown', f'{user}:{user}', str(superadmin_file)], check=False)
            run_command(['chmod', '600', str(superadmin_file)], check=False)
            print_success("Superadmin configured with secure permissions (600)")
        
        return True
    
    except Exception as e:
        print_error(f"Error during superadmin setup: {e}")
        if setup_script.exists():
            setup_script.unlink()
        return False


# ============================================================================
# System Verification (System 2.0)
# ============================================================================

def run_verification(project_dir: Path) -> bool:
    """
    Run system verification using verify.sh if available.
    
    Args:
        project_dir: Project directory path
    
    Returns:
        True if verification passed, False otherwise
    """
    print_header("System Verification")
    
    verify_script = project_dir / 'verify.sh'
    
    if not verify_script.exists():
        print_warning("verify.sh not found, skipping verification")
        return True
    
    print_info("Running system verification...")
    
    # Run verify.sh with --skip-i2c since system hasn't been rebooted yet
    success, stdout, stderr = run_command(
        ['bash', str(verify_script), '--skip-i2c'],
        timeout=60,
        check=False
    )
    
    # Print output
    if stdout:
        print(stdout)
    
    if success:
        print_success("System verification passed")
        return True
    else:
        print_warning("System verification found issues")
        print_info("This is expected before reboot (I2C not yet active)")
        return True  # Don't fail installation for verification issues


# ============================================================================
# Hardware Tests Offer (System 2.0)
# ============================================================================

def offer_hardware_tests(project_dir: Path) -> None:
    """
    Inform user about available hardware tests.
    
    Args:
        project_dir: Project directory path
    """
    print_header("Hardware Tests Available")
    
    print_info("Hardware test scripts are available to verify PLC connection:")
    print()
    print("  • relay_test.py   - Test relays and inputs")
    print("  • email_test.py   - Test email notifications")
    print()
    print_info("Run these tests after reboot when I2C is activated:")
    print()
    print(f"  cd {project_dir}")
    print("  source .venv/bin/activate")
    print("  python3 relay_test.py --host <plc-ip>")
    print("  python3 email_test.py")
    print()


# ============================================================================
# systemd Services Installation
# ============================================================================

def install_systemd_services(project_dir: Path, user: str) -> bool:
    """
    Install and enable systemd services.
    
    Args:
        project_dir: Project directory path
        user: User to run services as
    
    Returns:
        True if successful, False otherwise
    """
    print_header("systemd Services Installation")
    
    services = [
        'systemd_bevattning-api.service',
        'systemd_bevattning-scheduler.service',
        'systemd_bevattning-scheduler.timer',
        'systemd_display-manager.service',
    ]
    
    print_info("The following systemd services will be installed:")
    for svc in services:
        print(f"  • {svc}")
    print()
    
    if not get_yes_no("Install and enable systemd services?", default=True):
        print_info("Skipping systemd services installation")
        return True
    
    installed_services = []
    
    for service_file in services:
        src_path = project_dir / service_file
        
        if not src_path.exists():
            print_warning(f"{service_file} not found, skipping")
            continue
        
        # Read service file and update paths
        try:
            content = src_path.read_text()
            
            # Replace /home/pi with actual paths
            content = content.replace('/home/pi/fotbollsplan-bevattning', str(project_dir))
            
            # Update User and Group
            content = re.sub(r'^User=.*$', f'User={user}', content, flags=re.MULTILINE)
            content = re.sub(r'^Group=.*$', f'Group={user}', content, flags=re.MULTILINE)
            
            # Write to /etc/systemd/system
            dest_path = Path('/etc/systemd/system') / service_file.replace('systemd_', '')
            
            with open(dest_path, 'w') as f:
                f.write(content)
            
            print_success(f"Installed {dest_path.name}")
            installed_services.append(dest_path.name)
            
        except Exception as e:
            print_error(f"Failed to install {service_file}: {e}")
            continue
    
    if not installed_services:
        print_warning("No services were installed")
        return True
    
    # Create bevattning-controller.service for System 2.0
    print_info("Creating bevattning-controller.service (System 2.0)...")
    controller_service_content = f"""[Unit]
Description=Bevattning Controller (System 2.0)
After=network-online.target
Wants=network-online.target

[Service]
User={user}
Group={user}
WorkingDirectory={project_dir}
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile={project_dir}/api_.env
ExecStart={project_dir}/.venv/bin/python3 {project_dir}/bevattning_controller.py --loop --interval 60 --read-markfukt
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    controller_service_path = Path('/etc/systemd/system/bevattning-controller.service')
    try:
        with open(controller_service_path, 'w') as f:
            f.write(controller_service_content)
        print_success("Created bevattning-controller.service")
        installed_services.append('bevattning-controller.service')
    except Exception as e:
        print_error(f"Failed to create bevattning-controller.service: {e}")
    
    # Reload systemd daemon
    print_info("Reloading systemd daemon...")
    success, _, stderr = run_command(['systemctl', 'daemon-reload'])
    if not success:
        print_error(f"Failed to reload systemd: {stderr}")
        return False
    
    # Enable and start services
    print_info("\nEnabling and starting services...")
    
    for service in installed_services:
        if service.endswith('.timer'):
            # Enable but don't start timers (they start their .service)
            print_info(f"Enabling {service}...")
            success, _, stderr = run_command(['systemctl', 'enable', service], check=False)
            if success:
                print_success(f"Enabled {service}")
                # Start the timer
                run_command(['systemctl', 'start', service], check=False)
            else:
                print_error(f"Failed to enable {service}: {stderr}")
        
        elif service.endswith('.service'):
            # Enable and start services
            print_info(f"Enabling and starting {service}...")
            success, _, stderr = run_command(['systemctl', 'enable', service], check=False)
            if success:
                print_success(f"Enabled {service}")
            else:
                print_error(f"Failed to enable {service}: {stderr}")
            
            # Start the service
            success, _, stderr = run_command(['systemctl', 'start', service], check=False, timeout=30)
            if success:
                print_success(f"Started {service}")
            else:
                print_warning(f"Failed to start {service}: {stderr}")
                print_info(f"Check status with: systemctl status {service}")
    
    print_success("\nAll services installed and configured")
    
    return True


# ============================================================================
# Main Installation Flow
# ============================================================================

def main() -> int:
    """Main installation function."""
    # Ensure script is run as root
    if os.geteuid() != 0:
        print_error("ERROR: This script must be run as root (use sudo)")
        print_error("Usage: sudo python3 install_complete.py")
        return 1
    
    print_header("Fotbollsplan-bevattning - Komplett Installation (System 2.0)")
    print_info("Raspberry Pi 4 - Debian Bookworm Lite\n")
    
    print("Denna installation kommer att:")
    print("  1. Konfigurera WiFi-nätverk")
    print("  2. Installera systempaket")
    print("  3. Konfigurera I2C för Display 1 och Arkadknappar")
    print("  4. Skapa Python virtual environment")
    print("  5. Konfigurera miljövariabler (API, Modbus, SMTP)")
    print("  6. Skapa superadmin-användare")
    print("  7. Installera Tailscale (valfritt)")
    print("  8. Installera och aktivera systemd-tjänster")
    print("  9. Verifiera systemet")
    print()
    
    if not get_yes_no("Vill du fortsätta med installationen?", default=True):
        print_info("Installation avbruten")
        return 0
    
    # Determine project directory
    project_dir = Path(__file__).parent.resolve()
    user = os.getenv('SUDO_USER', DEFAULT_USER)
    
    print_info(f"Project directory: {project_dir}")
    print_info(f"Installation user: {user}\n")
    
    # Step 1: WiFi Configuration
    if not setup_wifi():
        print_error("WiFi configuration failed")
        if not get_yes_no("Continue anyway?", default=False):
            return 1
    
    # Step 2: System Package Installation
    if not install_system_packages():
        print_error("System package installation failed")
        if not get_yes_no("Continue anyway?", default=False):
            return 1
    
    # Step 3: I2C Configuration
    if not enable_i2c():
        print_error("I2C configuration failed")
        if not get_yes_no("Continue anyway?", default=True):
            return 1
    
    # Step 4: Python Environment Setup
    if not setup_python_environment(project_dir, user):
        print_error("Python environment setup failed")
        if not get_yes_no("Continue anyway?", default=False):
            return 1
    
    # Step 5: Environment Configuration
    if not configure_environment(project_dir, user):
        print_error("Environment configuration failed")
        if not get_yes_no("Continue anyway?", default=False):
            return 1
    
    # Step 5.5: Superadmin Setup (System 2.0)
    if not setup_superadmin(project_dir, user):
        print_warning("Superadmin setup failed or was skipped")
        # Continue anyway - not critical
    
    # Step 6: Tailscale Setup
    if not setup_tailscale():
        print_warning("Tailscale setup failed or was skipped")
        # Continue anyway - Tailscale is optional
    
    # Step 7: systemd Services Installation
    if not install_systemd_services(project_dir, user):
        print_error("systemd services installation failed")
        if not get_yes_no("Continue anyway?", default=True):
            return 1
    
    # Step 8: System Verification (System 2.0)
    run_verification(project_dir)
    
    # Step 9: Offer Hardware Tests (System 2.0)
    offer_hardware_tests(project_dir)
    
    # Final summary
    print_header("Installation Complete!")
    
    print_success("Fotbollsplan-bevattning System 2.0 har installerats framgångsrikt!\n")
    
    print("Nästa steg:")
    print("  1. Starta om systemet för att aktivera alla ändringar:")
    print("     sudo reboot")
    print()
    print("  2. Efter omstart, verifiera I2C-enheter:")
    print("     i2cdetect -y 1")
    print("     (Du ska se: 0x27 för Display 1, 0x20 för Arkadknappar)")
    print()
    print("  3. Kontrollera tjänsternas status:")
    print("     systemctl status bevattning-controller")
    print("     systemctl status bevattning-api")
    print("     systemctl status display-manager")
    print()
    print("  4. Få åtkomst till webb-UI:")
    print("     http://<raspberry-pi-ip>:8000")
    print("     (Använd API-nyckeln du konfigurerade)")
    print()
    print("  5. Kör hårdvarutester:")
    print(f"     cd {project_dir}")
    print("     source .venv/bin/activate")
    print("     python3 relay_test.py --host <plc-ip>")
    print("     python3 email_test.py")
    print()
    print("  6. Kontrollera loggar vid behov:")
    print("     journalctl -u bevattning-controller -f")
    print("     journalctl -u bevattning-api -f")
    print("     journalctl -u display-manager -f")
    print()
    
    if Path('/usr/bin/tailscale').exists():
        print("  5. Tailscale fjärråtkomst:")
        print("     sudo tailscale status")
        print("     sudo tailscale ip")
        print()
    
    print("Se README.md för fullständig dokumentation och användning.")
    print()
    
    if get_yes_no("Vill du starta om systemet nu?", default=True):
        print_info("Startar om systemet...")
        time.sleep(2)
        run_command(['reboot'], check=False)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInstallation avbruten av användaren.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Oväntat fel: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
