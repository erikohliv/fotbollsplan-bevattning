#!/usr/bin/env python3
"""
Test script for install_complete.py

This script validates the structure and basic functionality of install_complete.py
without actually executing system commands.
"""

import sys
import os
from pathlib import Path

# Add project directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all required imports are available."""
    print("Testing imports...")
    try:
        import install_complete
        print("✓ install_complete module imports successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import install_complete: {e}")
        return False


def test_constants():
    """Test that all required constants are defined."""
    print("\nTesting constants...")
    import install_complete
    
    required_constants = [
        'DEFAULT_API_KEY',
        'DEFAULT_MODBUS_HOST',
        'DEFAULT_MODBUS_PORT',
        'DEFAULT_MODBUS_UNIT',
        'DEFAULT_SMTP_HOST',
        'DEFAULT_SMTP_PORT',
        'REQUIRED_PACKAGES',
    ]
    
    all_ok = True
    for const in required_constants:
        if hasattr(install_complete, const):
            value = getattr(install_complete, const)
            print(f"✓ {const} = {value}")
        else:
            print(f"✗ Missing constant: {const}")
            all_ok = False
    
    return all_ok


def test_functions_exist():
    """Test that all required functions exist."""
    print("\nTesting function definitions...")
    import install_complete
    
    required_functions = [
        'print_header',
        'print_success',
        'print_error',
        'print_info',
        'get_input',
        'get_yes_no',
        'run_command',
        'validate_ipv4',
        'validate_port',
        'validate_email',
        'scan_wifi_networks',
        'configure_wifi',
        'setup_wifi',
        'update_apt_cache',
        'install_system_packages',
        'enable_i2c',
        'setup_python_environment',
        'configure_environment',
        'setup_tailscale',
        'install_systemd_services',
        'main',
    ]
    
    all_ok = True
    for func_name in required_functions:
        if hasattr(install_complete, func_name):
            func = getattr(install_complete, func_name)
            if callable(func):
                print(f"✓ {func_name}() is defined")
            else:
                print(f"✗ {func_name} exists but is not callable")
                all_ok = False
        else:
            print(f"✗ Missing function: {func_name}")
            all_ok = False
    
    return all_ok


def test_validators():
    """Test validator functions."""
    print("\nTesting validators...")
    import install_complete
    
    # Test IP validation
    test_cases_ip = [
        ('192.168.1.1', True),
        ('127.0.0.1', True),
        ('255.255.255.255', True),
        ('0.0.0.0', True),
        ('256.1.1.1', False),
        ('192.168.1', False),
        ('abc.def.ghi.jkl', False),
        ('', False),
    ]
    
    all_ok = True
    for ip, expected in test_cases_ip:
        result = install_complete.validate_ipv4(ip)
        if result == expected:
            print(f"✓ validate_ipv4('{ip}') = {result}")
        else:
            print(f"✗ validate_ipv4('{ip}') = {result}, expected {expected}")
            all_ok = False
    
    # Test port validation
    test_cases_port = [
        ('80', (True, 80)),
        ('8000', (True, 8000)),
        ('65535', (True, 65535)),
        ('1', (True, 1)),
        ('0', (False, 0)),
        ('65536', (False, 0)),
        ('abc', (False, 0)),
        ('', (False, 0)),
    ]
    
    for port_str, expected in test_cases_port:
        result = install_complete.validate_port(port_str)
        if result == expected:
            print(f"✓ validate_port('{port_str}') = {result}")
        else:
            print(f"✗ validate_port('{port_str}') = {result}, expected {expected}")
            all_ok = False
    
    # Test email validation
    test_cases_email = [
        ('user@example.com', True),
        ('test.user@domain.co.uk', True),
        ('name+tag@example.com', True),
        ('invalid', False),
        ('no@domain', False),
        ('@example.com', False),
        ('user@', False),
        ('', False),
    ]
    
    for email, expected in test_cases_email:
        result = install_complete.validate_email(email)
        if result == expected:
            print(f"✓ validate_email('{email}') = {result}")
        else:
            print(f"✗ validate_email('{email}') = {result}, expected {expected}")
            all_ok = False
    
    return all_ok


def test_required_packages():
    """Test that required packages list is reasonable."""
    print("\nTesting required packages list...")
    import install_complete
    
    packages = install_complete.REQUIRED_PACKAGES
    
    essential_packages = [
        'python3',
        'python3-pip',
        'python3-venv',
        'i2c-tools',
        'git',
    ]
    
    all_ok = True
    for pkg in essential_packages:
        if pkg in packages:
            print(f"✓ Essential package '{pkg}' is in REQUIRED_PACKAGES")
        else:
            print(f"✗ Missing essential package: {pkg}")
            all_ok = False
    
    print(f"\nTotal packages to install: {len(packages)}")
    
    return all_ok


def test_script_structure():
    """Test the script file structure."""
    print("\nTesting script structure...")
    
    script_path = Path(__file__).parent / 'install_complete.py'
    
    if not script_path.exists():
        print(f"✗ Script not found: {script_path}")
        return False
    
    print(f"✓ Script exists: {script_path}")
    
    # Check if executable
    if os.access(script_path, os.X_OK):
        print("✓ Script is executable")
    else:
        print("⚠ Script is not executable (run: chmod +x install_complete.py)")
    
    # Check shebang
    with open(script_path, 'r') as f:
        first_line = f.readline()
        if first_line.startswith('#!/usr/bin/env python3'):
            print("✓ Correct shebang line")
        else:
            print(f"✗ Incorrect shebang: {first_line.strip()}")
    
    # Check for root check
    content = script_path.read_text()
    if 'os.geteuid() != 0' in content:
        print("✓ Root privilege check present")
    else:
        print("⚠ Root privilege check not found")
    
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("  Testing install_complete.py")
    print("=" * 70)
    
    tests = [
        ("Imports", test_imports),
        ("Constants", test_constants),
        ("Functions", test_functions_exist),
        ("Validators", test_validators),
        ("Required Packages", test_required_packages),
        ("Script Structure", test_script_structure),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' raised exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("  Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
