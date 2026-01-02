#!/usr/bin/env python3
"""
Demo script showing how to use the user management functionality.

This script demonstrates:
1. Setting up a superadmin password
2. Creating users with different privilege levels
3. Listing users
4. Deleting users
5. Verifying user credentials
"""

import sys
from pathlib import Path

# Import user management
try:
    from user_management import SuperAdminManager, UserManager
except ImportError:
    print("Error: user_management module not found.")
    print("Make sure you've installed passlib: pip install passlib[bcrypt]")
    sys.exit(1)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def demo_superadmin_setup():
    """Demonstrate superadmin password setup."""
    print_section("1. Superadmin Password Setup")
    
    # Create superadmin manager (uses 'superadmin.txt' by default)
    superadmin = SuperAdminManager("demo_superadmin.txt")
    
    # Check if already configured
    if superadmin.is_configured():
        print("Superadmin password already exists.")
        print("For demo purposes, we'll use the existing password.\n")
    else:
        # Set a password
        password = "DemoSuperAdmin123"
        superadmin.set_password(password)
        print(f"✓ Superadmin password set to: {password}")
        print("  (In production, use a strong, unique password!)\n")
    
    # Verify the password
    if superadmin.verify_password("DemoSuperAdmin123"):
        print("✓ Password verification successful")
    else:
        print("✗ Password verification failed")
    
    return superadmin


def demo_user_creation():
    """Demonstrate user creation."""
    print_section("2. Creating Users")
    
    # Create user manager (uses 'users.json' by default)
    user_mgr = UserManager("demo_users.json")
    
    # Create a regular user
    print("Creating regular user 'operator1'...")
    success = user_mgr.create_user("operator1", "operator-password-123", is_admin=False)
    if success:
        print("✓ User 'operator1' created successfully\n")
    else:
        print("✗ User 'operator1' already exists\n")
    
    # Create an admin user
    print("Creating admin user 'admin1'...")
    success = user_mgr.create_user("admin1", "admin-password-456", is_admin=True)
    if success:
        print("✓ User 'admin1' created successfully\n")
    else:
        print("✗ User 'admin1' already exists\n")
    
    # Create another regular user
    print("Creating regular user 'operator2'...")
    success = user_mgr.create_user("operator2", "operator-password-789", is_admin=False)
    if success:
        print("✓ User 'operator2' created successfully\n")
    else:
        print("✗ User 'operator2' already exists\n")
    
    # Try to create a duplicate user (should fail)
    print("Attempting to create duplicate user 'operator1'...")
    success = user_mgr.create_user("operator1", "different-password", is_admin=False)
    if not success:
        print("✓ Duplicate user correctly rejected\n")
    else:
        print("✗ Duplicate user was incorrectly created\n")
    
    # Try to create a user with weak password (should fail)
    print("Attempting to create user with weak password...")
    try:
        user_mgr.create_user("weakuser", "weak", is_admin=False)
        print("✗ Weak password was incorrectly accepted\n")
    except ValueError as e:
        print(f"✓ Weak password correctly rejected: {e}\n")
    
    return user_mgr


def demo_list_users(user_mgr):
    """Demonstrate listing users."""
    print_section("3. Listing Users")
    
    users = user_mgr.list_users()
    
    print(f"Total users: {len(users)}\n")
    
    for user in users:
        admin_status = "Admin" if user['is_admin'] else "Regular User"
        print(f"  • {user['username']:20} ({admin_status})")
    
    print()


def demo_verify_credentials(user_mgr):
    """Demonstrate credential verification."""
    print_section("4. Verifying User Credentials")
    
    # Test correct credentials
    print("Verifying user 'operator1' with correct password...")
    user = user_mgr.verify_user("operator1", "operator-password-123")
    if user:
        print(f"✓ Credentials verified for: {user['username']}")
        print(f"  Admin status: {user['is_admin']}\n")
    else:
        print("✗ Credential verification failed\n")
    
    # Test incorrect password
    print("Verifying user 'operator1' with incorrect password...")
    user = user_mgr.verify_user("operator1", "wrong-password")
    if user is None:
        print("✓ Invalid password correctly rejected\n")
    else:
        print("✗ Invalid password was incorrectly accepted\n")
    
    # Test non-existent user
    print("Verifying non-existent user...")
    user = user_mgr.verify_user("nonexistent", "any-password")
    if user is None:
        print("✓ Non-existent user correctly rejected\n")
    else:
        print("✗ Non-existent user was incorrectly accepted\n")


def demo_delete_user(user_mgr):
    """Demonstrate user deletion."""
    print_section("5. Deleting Users")
    
    print("Deleting user 'operator2'...")
    success = user_mgr.delete_user("operator2")
    if success:
        print("✓ User 'operator2' deleted successfully\n")
    else:
        print("✗ User 'operator2' not found\n")
    
    # Verify deletion
    print("Verifying deletion...")
    users = user_mgr.list_users()
    if not any(u['username'] == 'operator2' for u in users):
        print("✓ User 'operator2' confirmed deleted\n")
    else:
        print("✗ User 'operator2' still exists\n")
    
    print(f"Remaining users: {len(users)}")
    for user in users:
        print(f"  • {user['username']}")
    print()


def cleanup():
    """Clean up demo files."""
    print_section("Cleanup")
    
    demo_files = ["demo_superadmin.txt", "demo_users.json"]
    
    for filename in demo_files:
        filepath = Path(filename)
        if filepath.exists():
            filepath.unlink()
            print(f"✓ Deleted {filename}")
    
    print("\nDemo complete!")


def main():
    """Run the demo."""
    print("\n" + "=" * 60)
    print("  User Management Demo - Fotbollsplan Bevattning")
    print("=" * 60)
    
    try:
        # 1. Setup superadmin
        superadmin = demo_superadmin_setup()
        
        # 2. Create users
        user_mgr = demo_user_creation()
        
        # 3. List users
        demo_list_users(user_mgr)
        
        # 4. Verify credentials
        demo_verify_credentials(user_mgr)
        
        # 5. Delete a user
        demo_delete_user(user_mgr)
        
        # Cleanup
        cleanup()
        
        print("\n" + "=" * 60)
        print("  All demo operations completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
