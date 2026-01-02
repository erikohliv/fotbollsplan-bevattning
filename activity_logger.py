"""
Activity Logger för Bevattningssystem
Loggar användaraktiviteter och systemhändelser
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ACTIVITY_LOG_FILE = Path(__file__).parent / "activity_log.json"
MAX_LOG_ENTRIES = 100  # Behåll max 100 entries


def log_activity(
    action: str,
    user: str = "system",
    zone: Optional[int] = None,
    details: Optional[Dict] = None
):
    """Logga en aktivitet"""
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "time": datetime.now().strftime("%H:%M"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "user": user,
        "action": action,
        "zone": zone,
        "details": details or {}
    }
    
    # Läs befintlig logg
    if ACTIVITY_LOG_FILE.exists():
        try:
            with open(ACTIVITY_LOG_FILE, 'r') as f:
                log_data = json.load(f)
        except:
            log_data = []
    else:
        log_data = []
    
    # Lägg till ny entry först
    log_data.insert(0, entry)
    
    # Begränsa storlek
    log_data = log_data[:MAX_LOG_ENTRIES]
    
    # Spara
    with open(ACTIVITY_LOG_FILE, 'w') as f:
        json.dump(log_data, f, indent=2)
    
    return entry


def get_activity_log(limit: int = 20) -> List[Dict]:
    """Hämta aktivitetslogg"""
    
    if not ACTIVITY_LOG_FILE.exists():
        return []
    
    try:
        with open(ACTIVITY_LOG_FILE, 'r') as f:
            log_data = json.load(f)
        return log_data[:limit]
    except:
        return []


def clear_activity_log():
    """Rensa aktivitetslogg"""
    if ACTIVITY_LOG_FILE.exists():
        ACTIVITY_LOG_FILE.unlink()
