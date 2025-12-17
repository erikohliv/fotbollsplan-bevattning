#!/usr/bin/env python3
"""
Test script for install.py - simulates user input
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Import the install module
import install


def test_validation_functions():
    """Test input validation functions."""
    print("Testing validation functions...")
    
    # Test email validation
    assert install.validate_email('test@example.com') == True
    assert install.validate_email('user.name+tag@example.co.uk') == True
    assert install.validate_email('invalid-email') == False
    assert install.validate_email('test@') == False
    assert install.validate_email('@example.com') == False
    print("✓ Email validation works")
    
    # Test port validation
    valid, port = install.validate_port('587')
    assert valid == True and port == 587
    valid, port = install.validate_port('1')
    assert valid == True and port == 1
    valid, port = install.validate_port('65535')
    assert valid == True and port == 65535
    valid, port = install.validate_port('0')
    assert valid == False
    valid, port = install.validate_port('65536')
    assert valid == False
    valid, port = install.validate_port('abc')
    assert valid == False
    print("✓ Port validation works")


def test_env_file_operations():
    """Test loading and saving .env files."""
    print("\nTesting .env file operations...")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_env_file = Path(tmpdir) / "test.env"
        
        # Test saving
        env_vars = {
            'API_KEY': 'test-key',
            'SMTP_HOST': 'smtp.test.com',
            'SMTP_PORT': '587',
            'SMTP_USER': 'test@example.com',
        }
        install.save_env_file(test_env_file, env_vars)
        assert test_env_file.exists()
        print("✓ .env file created")
        
        # Test loading
        loaded_vars = install.load_existing_env(test_env_file)
        assert loaded_vars['API_KEY'] == 'test-key'
        assert loaded_vars['SMTP_HOST'] == 'smtp.test.com'
        assert loaded_vars['SMTP_PORT'] == '587'
        assert loaded_vars['SMTP_USER'] == 'test@example.com'
        print("✓ .env file loaded correctly")
        
        # Test updating
        env_vars['SMTP_HOST'] = 'smtp.updated.com'
        install.save_env_file(test_env_file, env_vars)
        loaded_vars = install.load_existing_env(test_env_file)
        assert loaded_vars['SMTP_HOST'] == 'smtp.updated.com'
        print("✓ .env file updated correctly")


def test_smtp_test_with_mock():
    """Test SMTP connection testing with mock."""
    print("\nTesting SMTP connection (mocked)...")
    
    with patch('install.smtplib.SMTP') as mock_smtp:
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock()
        
        # Test successful connection
        success, message = install.test_smtp_connection(
            'smtp.test.com', 587, 'test@example.com', 
            'password', 'test@example.com', 'recipient@example.com', False
        )
        
        assert success == True
        assert "successfully" in message.lower()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@example.com', 'password')
        mock_server.send_message.assert_called_once()
        print("✓ SMTP test function works (mocked)")


def test_full_workflow():
    """Test the full workflow components."""
    print("\nTesting workflow components...")
    
    # Just test that the key functions work together
    with tempfile.TemporaryDirectory() as tmpdir:
        test_env_file = Path(tmpdir) / "test.env"
        
        # Simulate a complete configuration
        env_vars = {
            'API_KEY': 'test-key',
            'MODBUS_HOST': '127.0.0.1',
            'MODBUS_PORT': '502',
            'MODBUS_UNIT': '1',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USER': 'test@example.com',
            'SMTP_PASS': 'testpassword',
            'SMTP_FROM': 'test@example.com',
            'SMTP_TO': 'recipient@example.com',
            'SMTP_TIMEOUT': '10',
        }
        
        # Save and reload
        install.save_env_file(test_env_file, env_vars)
        loaded = install.load_existing_env(test_env_file)
        
        # Verify all SMTP variables were saved and loaded
        for key in ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 
                    'SMTP_FROM', 'SMTP_TO', 'SMTP_TIMEOUT']:
            assert key in loaded, f"{key} not found in loaded env"
            assert loaded[key] == env_vars[key], f"{key} value mismatch"
        
        print("✓ Workflow components work correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("  Testing install.py")
    print("=" * 60 + "\n")
    
    try:
        test_validation_functions()
        test_env_file_operations()
        test_smtp_test_with_mock()
        test_full_workflow()
        
        print("\n" + "=" * 60)
        print("  All tests passed! ✓")
        print("=" * 60)
        return 0
    
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
