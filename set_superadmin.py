#!/usr/bin/env python3
"""Temporary script to set superadmin password."""
import getpass
from user_management import SuperAdminManager

sm = SuperAdminManager()

print("Superadmin lösenord (max 72 tecken)")
while True:
    pw = getpass.getpass('Ange lösenord: ')
    if len(pw) > 72:
        print("✗ Lösenordet är för långt (max 72 tecken)")
        continue
    if len(pw) < 8:
        print("✗ Lösenordet är för kort (min 8 tecken)")
        continue
    
    pw2 = getpass.getpass('Bekräfta: ')
    if pw != pw2:
        print("✗ Lösenorden matchar inte")
        continue
    
    try:
        sm.set_password(pw)
        print("✓ Superadmin-lösenord satt!")
        break
    except Exception as e:
        print(f"✗ Fel: {e}")
        break
