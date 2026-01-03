#!/usr/bin/env python3
"""
Test script för att skicka ett exempel på välkomstmail
"""
import os
import sys
from dotenv import load_dotenv

# Ladda miljövariabler
load_dotenv("api_.env")

# Lägg till projektets root i Python path
sys.path.insert(0, os.path.dirname(__file__))

# Importera send_welcome_email från api_main
from api_main import send_welcome_email

# Testdata
test_email = "erik.ohliv@gmail.com"
test_username = "testuser"
test_password = "TempPass123!"
test_is_admin = False

print("=" * 60)
print("SKICKAR TEST-VÄLKOMSTMAIL")
print("=" * 60)
print(f"Till: {test_email}")
print(f"Användarnamn: {test_username}")
print(f"Lösenord: {test_password}")
print(f"Roll: {'Administratör' if test_is_admin else 'Operatör'}")
print("=" * 60)
print()

# Skicka mailet
success = send_welcome_email(
    email=test_email,
    username=test_username,
    temp_password=test_password,
    is_admin=test_is_admin
)

if success:
    print("✅ Välkomstmail skickat!")
    print(f"Kontrollera din inkorg: {test_email}")
else:
    print("❌ Kunde inte skicka välkomstmail")
    print("Kontrollera SMTP-inställningar i api_.env")

