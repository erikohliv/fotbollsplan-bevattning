# User Management API Documentation

## Overview

The Fotbollsplan-bevattning system now includes user management functionality protected by superadmin authentication. This allows the superadmin to create, manage, and delete user accounts that can access the irrigation system.

## Setup

### 1. Initial Superadmin Setup

During installation, run the setup script to configure the superadmin password:

```bash
python3 setup.py
```

The setup script will prompt you to:
1. Set a superadmin password (minimum 8 characters)
2. Confirm the password

The password is securely hashed using bcrypt and stored in `superadmin.txt`.

### 2. Manual Superadmin Setup

If you need to set or change the superadmin password manually:

```python
from user_management import SuperAdminManager

superadmin = SuperAdminManager()
superadmin.set_password("your-secure-password-here")
```

## API Endpoints

All user management endpoints require HTTP Basic Authentication with superadmin credentials.

### Create a User

**Endpoint:** `POST /users/create`

**Authentication:** HTTP Basic Auth (superadmin credentials)

**Request Body:**
```json
{
  "username": "newuser",
  "password": "securepassword123",
  "is_admin": false
}
```

**Response:**
```json
{
  "ok": true,
  "message": "User 'newuser' created successfully",
  "username": "newuser",
  "is_admin": false
}
```

**Example with curl:**
```bash
curl -X POST http://localhost:8000/users/create \
  -u "superadmin:your-password" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "password": "operator-password-123",
    "is_admin": false
  }'
```

### Delete a User

**Endpoint:** `POST /users/delete`

**Authentication:** HTTP Basic Auth (superadmin credentials)

**Request Body:**
```json
{
  "username": "userToDelete"
}
```

**Response:**
```json
{
  "ok": true,
  "message": "User 'userToDelete' deleted successfully",
  "username": "userToDelete"
}
```

**Example with curl:**
```bash
curl -X POST http://localhost:8000/users/delete \
  -u "superadmin:your-password" \
  -H "Content-Type: application/json" \
  -d '{"username": "operator1"}'
```

### List Users

**Endpoint:** `GET /users/list`

**Authentication:** HTTP Basic Auth (superadmin credentials)

**Response:**
```json
{
  "ok": true,
  "users": [
    {
      "username": "operator1",
      "is_admin": false
    },
    {
      "username": "admin1",
      "is_admin": true
    }
  ],
  "count": 2
}
```

**Example with curl:**
```bash
curl -X GET http://localhost:8000/users/list \
  -u "superadmin:your-password"
```

## Python Usage Examples

### Using the User Management API

```python
import requests
from requests.auth import HTTPBasicAuth

# API configuration
API_URL = "http://localhost:8000"
SUPERADMIN_USER = "superadmin"
SUPERADMIN_PASS = "your-superadmin-password"

# Create authentication
auth = HTTPBasicAuth(SUPERADMIN_USER, SUPERADMIN_PASS)

# Create a user
response = requests.post(
    f"{API_URL}/users/create",
    json={
        "username": "operator1",
        "password": "operator-password-123",
        "is_admin": False
    },
    auth=auth
)
print(response.json())

# List users
response = requests.get(f"{API_URL}/users/list", auth=auth)
print(response.json())

# Delete a user
response = requests.post(
    f"{API_URL}/users/delete",
    json={"username": "operator1"},
    auth=auth
)
print(response.json())
```

### Direct User Management (without API)

```python
from user_management import SuperAdminManager, UserManager

# Setup superadmin
superadmin = SuperAdminManager()
if not superadmin.is_configured():
    superadmin.set_password("secure-superadmin-password")

# Manage users
user_mgr = UserManager()

# Create a user
user_mgr.create_user("operator1", "password123", is_admin=False)

# List users
users = user_mgr.list_users()
for user in users:
    print(f"Username: {user['username']}, Admin: {user['is_admin']}")

# Verify user credentials
user = user_mgr.verify_user("operator1", "password123")
if user:
    print(f"User authenticated: {user['username']}")

# Delete a user
user_mgr.delete_user("operator1")
```

## Security Features

1. **Password Hashing:** All passwords are hashed using bcrypt before storage
2. **Minimum Password Length:** Passwords must be at least 8 characters long
3. **Secure File Permissions:** User data files are created with 0600 permissions (owner read/write only)
4. **HTTP Basic Authentication:** Superadmin endpoints use industry-standard HTTP Basic Auth
5. **No Password Exposure:** Password hashes are never returned in API responses

## File Storage

- **superadmin.txt:** Stores the hashed superadmin password
- **users.json:** Stores user accounts with hashed passwords

Both files are created with restrictive permissions (0600) to prevent unauthorized access.

## Error Handling

### Invalid Password
```json
{
  "detail": "Password must be at least 8 characters long"
}
```

### User Already Exists
```json
{
  "detail": "User 'username' already exists"
}
```

### User Not Found
```json
{
  "detail": "User 'username' not found"
}
```

### Invalid Superadmin Credentials
```json
{
  "detail": "Invalid superadmin credentials"
}
```

### Superadmin Not Configured
```json
{
  "detail": "Superadmin not configured - run setup.py first"
}
```

## Integration with Existing API

The user management system is separate from the existing API key authentication used for irrigation control. The existing endpoints continue to use the `X-API-Key` header for authentication:

```bash
# Existing irrigation control (uses API key)
curl -X POST http://localhost:8000/command/start-auto \
  -H "X-API-Key: your-api-key"

# User management (uses HTTP Basic Auth)
curl -X GET http://localhost:8000/users/list \
  -u "superadmin:your-password"
```

## Best Practices

1. **Strong Passwords:** Use strong, unique passwords for the superadmin and all user accounts
2. **HTTPS in Production:** Always use HTTPS in production to protect credentials in transit
3. **Regular Audits:** Periodically review the user list and remove inactive accounts
4. **Backup:** Keep secure backups of `superadmin.txt` and `users.json`
5. **Access Control:** Limit access to the server where these files are stored
