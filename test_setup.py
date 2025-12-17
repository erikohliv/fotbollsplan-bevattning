#!/usr/bin/env python3
"""
Test script for setup.py - validates validation functions and file operations
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Import the setup module
import setup


def test_validation_functions():
    """Test input validation functions."""
    print("Testing validation functions...")
    
    # Test IPv4 validation
    assert setup.validate_ipv4('127.0.0.1')
    assert setup.validate_ipv4('192.168.1.1')
    assert setup.validate_ipv4('10.0.0.1')
    assert setup.validate_ipv4('255.255.255.255')
    assert not setup.validate_ipv4('256.0.0.1')
    assert not setup.validate_ipv4('192.168.1')
    assert not setup.validate_ipv4('192.168.1.1.1')
    assert not setup.validate_ipv4('invalid-ip')
    assert not setup.validate_ipv4('localhost')
    print("✓ IPv4 validation works")
    
    # Test port validation
    valid, port = setup.validate_port('502')
    assert valid and port == 502
    valid, port = setup.validate_port('1')
    assert valid and port == 1
    valid, port = setup.validate_port('65535')
    assert valid and port == 65535
    valid, port = setup.validate_port('0')
    assert not valid
    valid, port = setup.validate_port('65536')
    assert not valid
    valid, port = setup.validate_port('abc')
    assert not valid
    print("✓ Port validation works")
    
    # Test unit ID validation
    valid, unit = setup.validate_unit_id('1')
    assert valid and unit == 1
    valid, unit = setup.validate_unit_id('128')
    assert valid and unit == 128
    valid, unit = setup.validate_unit_id('255')
    assert valid and unit == 255
    valid, unit = setup.validate_unit_id('0')
    assert not valid
    valid, unit = setup.validate_unit_id('256')
    assert not valid
    valid, unit = setup.validate_unit_id('abc')
    assert not valid
    print("✓ Unit ID validation works")


def test_env_file_operations():
    """Test loading and saving .env files."""
    print("\nTesting .env file operations...")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_env_file = Path(tmpdir) / "test.env"
        
        # Test saving
        env_vars = {
            'API_KEY': 'test-key-12345',
            'MODBUS_HOST': '192.168.1.100',
            'MODBUS_PORT': '502',
            'MODBUS_UNIT': '1',
            'SMTP_HOST': 'smtp.test.com',
            'SMTP_PORT': '587',
        }
        setup.save_env_file(test_env_file, env_vars)
        assert test_env_file.exists()
        print("✓ .env file created")
        
        # Test loading
        loaded_vars = setup.load_existing_env(test_env_file)
        assert loaded_vars['API_KEY'] == 'test-key-12345'
        assert loaded_vars['MODBUS_HOST'] == '192.168.1.100'
        assert loaded_vars['MODBUS_PORT'] == '502'
        assert loaded_vars['MODBUS_UNIT'] == '1'
        assert loaded_vars['SMTP_HOST'] == 'smtp.test.com'
        assert loaded_vars['SMTP_PORT'] == '587'
        print("✓ .env file loaded correctly")
        
        # Test updating
        env_vars['MODBUS_HOST'] = '10.0.0.1'
        env_vars['API_KEY'] = 'updated-key'
        setup.save_env_file(test_env_file, env_vars)
        loaded_vars = setup.load_existing_env(test_env_file)
        assert loaded_vars['MODBUS_HOST'] == '10.0.0.1'
        assert loaded_vars['API_KEY'] == 'updated-key'
        print("✓ .env file updated correctly")


def test_pip_check():
    """Test pip availability check."""
    print("\nTesting pip check...")
    
    # This should work in our test environment
    result = setup.check_pip()
    assert result is True
    print("✓ pip check works")


def test_tailscale_detection():
    """Test Tailscale installation detection."""
    print("\nTesting Tailscale detection...")
    
    # Just test that the function runs without error
    # It may or may not be installed in the test environment
    is_installed = setup.is_tailscale_installed()
    print(f"ℹ Tailscale installed: {is_installed}")
    print("✓ Tailscale detection works")


def test_ufw_detection():
    """Test ufw availability detection."""
    print("\nTesting ufw detection...")
    
    # Just test that the function runs without error
    is_available = setup.is_ufw_available()
    print(f"ℹ ufw available: {is_available}")
    print("✓ ufw detection works")


def test_full_workflow():
    """Test the full workflow components."""
    print("\nTesting workflow components...")
    
    # Test that the key functions work together
    with tempfile.TemporaryDirectory() as tmpdir:
        test_env_file = Path(tmpdir) / "test.env"
        
        # Simulate a complete configuration
        env_vars = {
            'API_KEY': 'workflow-test-key',
            'MODBUS_HOST': '127.0.0.1',
            'MODBUS_PORT': '502',
            'MODBUS_UNIT': '1',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_TIMEOUT': '10',
            'HEALTHCHECK_TIMEOUT': '5',
            'HEALTHCHECK_RETRIES': '3',
        }
        
        # Save and reload
        setup.save_env_file(test_env_file, env_vars)
        loaded = setup.load_existing_env(test_env_file)
        
        # Verify all required variables were saved and loaded
        for key in ['API_KEY', 'MODBUS_HOST', 'MODBUS_PORT', 'MODBUS_UNIT']:
            assert key in loaded, f"{key} not found in loaded env"
            assert loaded[key] == env_vars[key], f"{key} value mismatch"
        
        # Verify SMTP variables
        for key in ['SMTP_HOST', 'SMTP_PORT', 'SMTP_TIMEOUT']:
            assert key in loaded, f"{key} not found in loaded env"
            assert loaded[key] == env_vars[key], f"{key} value mismatch"
        
        # Verify healthcheck variables
        for key in ['HEALTHCHECK_TIMEOUT', 'HEALTHCHECK_RETRIES']:
            assert key in loaded, f"{key} not found in loaded env"
            assert loaded[key] == env_vars[key], f"{key} value mismatch"
        
        print("✓ Workflow components work correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("  Testing setup.py")
    print("=" * 60 + "\n")
    
    try:
        test_validation_functions()
        test_env_file_operations()
        test_pip_check()
        test_tailscale_detection()
        test_ufw_detection()
        test_full_workflow()
        
        print("\n" + "=" * 60)
        print("  All tests passed! ✓")
        print("=" * 60)
        return 0
    
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
