#!/usr/bin/env python3
"""
User Control Mode Manager
Hanterar "användarstyrning"-läge där alla inloggade användare kan styra systemet.

När användarstyrning är aktivt:
- Alla inloggade användare (via user_management) kan styra systemet
- API-nyckel krävs INTE längre
- Aktiveras via terminalkommando eller arcadknappar
"""

import json
import os
from pathlib import Path
from typing import Optional

# State file
STATE_FILE = Path.home() / '.user_control_state.json'


def is_user_control_enabled() -> bool:
    """Kontrollera om användarstyrning är aktivt."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('enabled', False)
    except Exception:
        pass
    return False


def set_user_control(enabled: bool, activated_by: str = "unknown") -> None:
    """Sätt användarstyrning-läge."""
    import time
    from datetime import datetime
    
    data = {
        'enabled': enabled,
        'activated_by': activated_by,
        'activated_at': datetime.now().isoformat(),
        'activated_timestamp': time.time()
    }
    
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Set restrictive permissions
    STATE_FILE.chmod(0o600)


def get_user_control_status() -> dict:
    """Hämta status för användarstyrning."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    
    return {
        'enabled': False,
        'activated_by': None,
        'activated_at': None,
        'activated_timestamp': 0
    }


if __name__ == '__main__':
    """CLI för att aktivera/deaktivera användarstyrning."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hantera användarstyrning-läge')
    parser.add_argument('action', choices=['enable', 'disable', 'status'], 
                       help='Aktivera, deaktivera eller visa status')
    parser.add_argument('--by', default='terminal', 
                       help='Vem som aktiverade (default: terminal)')
    
    args = parser.parse_args()
    
    if args.action == 'enable':
        set_user_control(True, args.by)
        print("✅ Användarstyrning AKTIVERAD")
        print("   Alla inloggade användare kan nu styra systemet")
        print("   API-nyckel krävs INTE längre")
    elif args.action == 'disable':
        set_user_control(False, args.by)
        print("🔒 Användarstyrning DEAKTIVERAD")
        print("   Endast användare med API-nyckel kan styra")
    elif args.action == 'status':
        status = get_user_control_status()
        if status['enabled']:
            print("✅ Användarstyrning är AKTIVT")
            print(f"   Aktiverad av: {status.get('activated_by', 'unknown')}")
            print(f"   Aktiverad: {status.get('activated_at', 'unknown')}")
        else:
            print("🔒 Användarstyrning är INAKTIVT")
            print("   Endast användare med API-nyckel kan styra")

