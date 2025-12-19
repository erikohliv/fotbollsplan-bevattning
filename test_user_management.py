#!/usr/bin/env python3
"""
Test suite for user management functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import base64

from fastapi.testclient import TestClient

# Import user management modules
from user_management import (
    SuperAdminManager,
    UserManager,
    hash_password,
    verify_password,
    validate_password_strength
)


def test_password_validation():
    """Test password strength validation."""
    assert validate_password_strength("12345678")  # 8 chars - valid
    assert validate_password_strength("verylongpassword123")  # Long password - valid
    assert not validate_password_strength("1234567")  # 7 chars - invalid
    assert not validate_password_strength("")  # Empty - invalid
    assert not validate_password_strength("short")  # Short - invalid


def test_password_hashing():
    """Test password hashing and verification."""
    password = "test-password-123"
    hashed = hash_password(password)
    
    # Hash should be different from password
    assert hashed != password
    
    # Verify correct password
    assert verify_password(password, hashed)
    
    # Verify incorrect password
    assert not verify_password("wrong-password", hashed)
    
    # Same password should produce different hashes
    hashed2 = hash_password(password)
    assert hashed != hashed2
    assert verify_password(password, hashed2)


def test_superadmin_manager():
    """Test SuperAdminManager functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        superadmin_file = Path(tmpdir) / "test_superadmin.txt"
        manager = SuperAdminManager(str(superadmin_file))
        
        # Initially not configured
        assert not manager.is_configured()
        
        # Set password
        password = "superadmin-password-123"
        manager.set_password(password)
        
        # Now should be configured
        assert manager.is_configured()
        
        # Verify correct password
        assert manager.verify_password(password)
        
        # Verify incorrect password
        assert not manager.verify_password("wrong-password")
        
        # Check file permissions (should be 0600)
        stat_info = superadmin_file.stat()
        permissions = oct(stat_info.st_mode)[-3:]
        assert permissions == "600"


def test_superadmin_manager_invalid_password():
    """Test SuperAdminManager rejects weak passwords."""
    with tempfile.TemporaryDirectory() as tmpdir:
        superadmin_file = Path(tmpdir) / "test_superadmin.txt"
        manager = SuperAdminManager(str(superadmin_file))
        
        # Try to set a weak password
        with pytest.raises(ValueError, match="at least 8 characters"):
            manager.set_password("short")


def test_user_manager_create_user():
    """Test UserManager user creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        users_file = Path(tmpdir) / "test_users.json"
        manager = UserManager(str(users_file))
        
        # Create a user
        success = manager.create_user("testuser", "password123", is_admin=False)
        assert success
        
        # Try to create the same user again
        success = manager.create_user("testuser", "password456", is_admin=False)
        assert not success
        
        # Create an admin user
        success = manager.create_user("admin", "adminpass123", is_admin=True)
        assert success


def test_user_manager_invalid_password():
    """Test UserManager rejects weak passwords."""
    with tempfile.TemporaryDirectory() as tmpdir:
        users_file = Path(tmpdir) / "test_users.json"
        manager = UserManager(str(users_file))
        
        # Try to create user with weak password
        with pytest.raises(ValueError, match="at least 8 characters"):
            manager.create_user("testuser", "weak")


def test_user_manager_delete_user():
    """Test UserManager user deletion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        users_file = Path(tmpdir) / "test_users.json"
        manager = UserManager(str(users_file))
        
        # Create users
        manager.create_user("user1", "password123")
        manager.create_user("user2", "password456")
        
        # Delete a user
        success = manager.delete_user("user1")
        assert success
        
        # Try to delete non-existent user
        success = manager.delete_user("user1")
        assert not success
        
        # Verify remaining user
        users = manager.list_users()
        assert len(users) == 1
        assert users[0]['username'] == "user2"


def test_user_manager_list_users():
    """Test UserManager listing users."""
    with tempfile.TemporaryDirectory() as tmpdir:
        users_file = Path(tmpdir) / "test_users.json"
        manager = UserManager(str(users_file))
        
        # Initially empty
        users = manager.list_users()
        assert len(users) == 0
        
        # Create users
        manager.create_user("user1", "password123", is_admin=False)
        manager.create_user("admin1", "adminpass123", is_admin=True)
        
        # List users
        users = manager.list_users()
        assert len(users) == 2
        
        # Verify user details (passwords should not be included)
        user1 = next(u for u in users if u['username'] == 'user1')
        assert user1['is_admin'] is False
        assert 'password_hash' not in user1
        assert 'password' not in user1
        
        admin1 = next(u for u in users if u['username'] == 'admin1')
        assert admin1['is_admin'] is True


def test_user_manager_verify_user():
    """Test UserManager user verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        users_file = Path(tmpdir) / "test_users.json"
        manager = UserManager(str(users_file))
        
        # Create a user
        manager.create_user("testuser", "password123", is_admin=False)
        
        # Verify with correct password
        user = manager.verify_user("testuser", "password123")
        assert user is not None
        assert user['username'] == "testuser"
        assert user['is_admin'] is False
        
        # Verify with incorrect password
        user = manager.verify_user("testuser", "wrongpassword")
        assert user is None
        
        # Verify non-existent user
        user = manager.verify_user("nonexistent", "password123")
        assert user is None


def test_user_manager_file_permissions():
    """Test UserManager sets proper file permissions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        users_file = Path(tmpdir) / "test_users.json"
        manager = UserManager(str(users_file))
        
        # Create a user
        manager.create_user("testuser", "password123")
        
        # Check file permissions (should be 0600)
        stat_info = users_file.stat()
        permissions = oct(stat_info.st_mode)[-3:]
        assert permissions == "600"


def test_api_endpoints_require_superadmin():
    """Test that user management API endpoints require superadmin auth."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Mock pymodbus
    sys.modules['pymodbus'] = MagicMock()
    sys.modules['pymodbus.client'] = MagicMock()
    
    from api_main import app
    
    client = TestClient(app)
    
    # Test without authentication
    response = client.post("/users/create", json={
        "username": "testuser",
        "password": "password123",
        "is_admin": False
    })
    assert response.status_code == 401
    
    response = client.post("/users/delete", json={"username": "testuser"})
    assert response.status_code == 401
    
    response = client.get("/users/list")
    assert response.status_code == 401


def test_api_create_user_endpoint():
    """Test the create user API endpoint with proper authentication."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Mock pymodbus
    sys.modules['pymodbus'] = MagicMock()
    sys.modules['pymodbus.client'] = MagicMock()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        superadmin_file = Path(tmpdir) / "test_superadmin.txt"
        users_file = Path(tmpdir) / "test_users.json"
        
        # Set up superadmin
        superadmin = SuperAdminManager(str(superadmin_file))
        superadmin.set_password("superadmin123")
        
        # Patch the managers in api_main
        with patch('api_main.superadmin_manager', superadmin):
            with patch('api_main.user_manager', UserManager(str(users_file))):
                from api_main import app
                client = TestClient(app)
                
                # Create Basic Auth header
                credentials = base64.b64encode(b"superadmin:superadmin123").decode('ascii')
                headers = {"Authorization": f"Basic {credentials}"}
                
                # Create user
                response = client.post("/users/create", 
                    json={
                        "username": "testuser",
                        "password": "password123",
                        "is_admin": False
                    },
                    headers=headers
                )
                assert response.status_code == 200
                data = response.json()
                assert data['ok'] is True
                assert data['username'] == "testuser"


def test_api_delete_user_endpoint():
    """Test the delete user API endpoint."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Mock pymodbus
    sys.modules['pymodbus'] = MagicMock()
    sys.modules['pymodbus.client'] = MagicMock()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        superadmin_file = Path(tmpdir) / "test_superadmin.txt"
        users_file = Path(tmpdir) / "test_users.json"
        
        # Set up superadmin
        superadmin = SuperAdminManager(str(superadmin_file))
        superadmin.set_password("superadmin123")
        
        # Create a user
        user_mgr = UserManager(str(users_file))
        user_mgr.create_user("testuser", "password123")
        
        # Patch the managers in api_main
        with patch('api_main.superadmin_manager', superadmin):
            with patch('api_main.user_manager', user_mgr):
                from api_main import app
                client = TestClient(app)
                
                credentials = base64.b64encode(b"superadmin:superadmin123").decode('ascii')
                headers = {"Authorization": f"Basic {credentials}"}
                
                # Delete user
                response = client.post("/users/delete",
                    json={"username": "testuser"},
                    headers=headers
                )
                assert response.status_code == 200
                data = response.json()
                assert data['ok'] is True


def test_api_list_users_endpoint():
    """Test the list users API endpoint."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Mock pymodbus
    sys.modules['pymodbus'] = MagicMock()
    sys.modules['pymodbus.client'] = MagicMock()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        superadmin_file = Path(tmpdir) / "test_superadmin.txt"
        users_file = Path(tmpdir) / "test_users.json"
        
        # Set up superadmin
        superadmin = SuperAdminManager(str(superadmin_file))
        superadmin.set_password("superadmin123")
        
        # Create users
        user_mgr = UserManager(str(users_file))
        user_mgr.create_user("user1", "password123", is_admin=False)
        user_mgr.create_user("admin1", "adminpass123", is_admin=True)
        
        # Patch the managers in api_main
        with patch('api_main.superadmin_manager', superadmin):
            with patch('api_main.user_manager', user_mgr):
                from api_main import app
                client = TestClient(app)
                
                credentials = base64.b64encode(b"superadmin:superadmin123").decode('ascii')
                headers = {"Authorization": f"Basic {credentials}"}
                
                # List users
                response = client.get("/users/list", headers=headers)
                assert response.status_code == 200
                data = response.json()
                assert data['ok'] is True
                assert data['count'] == 2
                assert len(data['users']) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
