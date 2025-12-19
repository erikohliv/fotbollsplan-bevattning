#!/usr/bin/env python3
"""
User management module for fotbollsplan-bevattning.

This module provides functionality for:
- Password hashing and verification
- Superadmin password setup and storage
- User account creation, deletion, and listing
- Secure storage of user credentials
"""

import json
import re
from pathlib import Path
from typing import Optional, List, Dict
from passlib.context import CryptContext


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> bool:
    """Validate that a password meets minimum requirements (at least 8 characters)."""
    return len(password) >= 8


def validate_username(username: str) -> bool:
    """
    Validate username format.
    
    Username must:
    - Be 3-32 characters long
    - Contain only alphanumeric characters, underscores, and hyphens
    - Start with an alphanumeric character
    """
    if not username or len(username) < 3 or len(username) > 32:
        return False
    
    # Check for valid characters and starting character
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$'
    return bool(re.match(pattern, username))


class SuperAdminManager:
    """Manages superadmin password storage and verification."""
    
    def __init__(self, file_path: str = "superadmin.txt"):
        self.file_path = Path(file_path)
    
    def set_password(self, password: str) -> None:
        """Set the superadmin password (hashed)."""
        if not validate_password_strength(password):
            raise ValueError("Password must be at least 8 characters long")
        
        hashed = hash_password(password)
        self.file_path.write_text(hashed)
        # Set restrictive permissions (only owner can read/write)
        self.file_path.chmod(0o600)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored superadmin password."""
        if not self.file_path.exists():
            return False
        
        stored_hash = self.file_path.read_text().strip()
        return verify_password(password, stored_hash)
    
    def is_configured(self) -> bool:
        """Check if superadmin password has been set."""
        return self.file_path.exists()


class UserManager:
    """Manages user accounts."""
    
    def __init__(self, file_path: str = "users.json"):
        self.file_path = Path(file_path)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Ensure users.json exists with proper permissions."""
        if not self.file_path.exists():
            self.file_path.write_text("[]")
        # Set restrictive permissions (only owner can read/write)
        self.file_path.chmod(0o600)
    
    def _load_users(self) -> List[Dict]:
        """Load users from JSON file."""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_users(self, users: List[Dict]) -> None:
        """Save users to JSON file."""
        with open(self.file_path, 'w') as f:
            json.dump(users, f, indent=2)
        # Ensure restrictive permissions
        self.file_path.chmod(0o600)
    
    def create_user(self, username: str, password: str, is_admin: bool = False) -> bool:
        """
        Create a new user.
        
        Args:
            username: Username for the new user
            password: Plain text password (will be hashed)
            is_admin: Whether the user has admin privileges
        
        Returns:
            True if user was created, False if username already exists
        
        Raises:
            ValueError: If password or username doesn't meet requirements
        """
        if not validate_username(username):
            raise ValueError("Username must be 3-32 characters, alphanumeric with underscores/hyphens, starting with alphanumeric")
        
        if not validate_password_strength(password):
            raise ValueError("Password must be at least 8 characters long")
        
        users = self._load_users()
        
        # Check if username already exists
        if any(u['username'] == username for u in users):
            return False
        
        # Add new user with hashed password
        users.append({
            'username': username,
            'password_hash': hash_password(password),
            'is_admin': is_admin
        })
        
        self._save_users(users)
        return True
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user by username.
        
        Returns:
            True if user was deleted, False if user not found
        """
        users = self._load_users()
        original_count = len(users)
        users = [u for u in users if u['username'] != username]
        
        if len(users) < original_count:
            self._save_users(users)
            return True
        return False
    
    def list_users(self) -> List[Dict]:
        """
        List all users (without password hashes).
        
        Returns:
            List of user dictionaries with username and is_admin fields
        """
        users = self._load_users()
        return [
            {
                'username': u['username'],
                'is_admin': u.get('is_admin', False)
            }
            for u in users
        ]
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Verify user credentials.
        
        Returns:
            User dict (without password) if credentials are valid, None otherwise
        """
        users = self._load_users()
        
        for user in users:
            if user['username'] == username:
                if verify_password(password, user['password_hash']):
                    return {
                        'username': user['username'],
                        'is_admin': user.get('is_admin', False)
                    }
        
        return None
