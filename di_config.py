"""
Digital Input Configuration
Definierar vad GPIO HIGH betyder för varje DI-ingång
"""

# DI-konfiguration: vad betyder GPIO HIGH?
DI_CONFIG = {
    # Index 0-11 motsvarar DI1-DI12
    
    # NO-kontakter (Normally Open): HIGH = Aktiverad/Tryckt
    0: {'name': 'Stoppknapp S202', 'type': 'NO', 'high_means': 'PRESSED', 'critical': False},
    1: {'name': 'Startknapp S201', 'type': 'NO', 'high_means': 'PRESSED', 'critical': False},
    3: {'name': 'Resetknapp S203', 'type': 'NO', 'high_means': 'PRESSED', 'critical': False},
    4: {'name': 'Auto-läge S204', 'type': 'NO', 'high_means': 'ACTIVE', 'critical': False, 'note': '⚙️  Återfjädrande vred, PLC latchar läge'},
    5: {'name': 'Manuell-läge S204', 'type': 'NO', 'high_means': 'ACTIVE', 'critical': False, 'note': '⚙️  Återfjädrande vred, PLC latchar läge'},
    6: {'name': 'Flödesvakt', 'type': 'NO', 'high_means': 'ALARM', 'critical': False},
    8: {'name': 'Tryckvakt', 'type': 'NO', 'high_means': 'ALARM', 'critical': False},
    
    # NC-kontakter (Normally Closed): HIGH = LARM/Fel
    2: {'name': 'Nödstopp S205', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': 'PLC blockerar (BlockReason=4). Måste vridas upp fysiskt!'},
    7: {'name': 'Mjukstartare Fault', 'type': 'NC', 'high_means': 'ALARM', 'critical': False, 'note': '🟡 PLC stoppar pump (BlockReason=8, auto-reset)'},
    9: {'name': 'Motorskydd Q1', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': 'PLC stoppar pump (BlockReason=7). Måste resetas på Q1!'},
    10: {'name': '24VDC Säkring', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': '⚠️  Ingen PLC-hantering. Säkring måste resetas/bytas!'},
    11: {'name': '24VAC Säkring', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': '[EJ INSTALLERAD] Säkring måste resetas/bytas vid fel'},
}


def get_di_info(index):
    """Hämta info för en DI-ingång (0-11)"""
    return DI_CONFIG.get(index, {
        'name': f'DI{index+1}',
        'type': 'NO',
        'high_means': 'ACTIVE',
        'critical': False,
        'note': None
    })


def is_alarm(index, gpio_state):
    """
    Avgör om en DI-ingång är i larmläge baserat på GPIO-tillstånd
    
    Args:
        index: DI index (0-11)
        gpio_state: GPIO-värde (True/False)
    
    Returns:
        True om larm, False om OK
    """
    config = get_di_info(index)
    
    if config['high_means'] == 'ALARM':
        # HIGH betyder larm (NC-kontakter, övervakningar)
        return gpio_state
    else:
        # För knappar/switchar finns inget "larm"
        return False


def is_di_ok(index, gpio_state):
    """
    Kontrollera om en DI är i OK-tillstånd (används i applikationslogik)
    
    Args:
        index: DI index (0-11)
        gpio_state: GPIO-värde (True/False eller 1/0)
    
    Returns:
        True om ingången är OK, False om larm/fel
    """
    config = get_di_info(index)
    gpio_bool = bool(gpio_state)
    
    if config['high_means'] == 'ALARM':
        # För NC och övervakningar: LOW=OK, HIGH=LARM
        return not gpio_bool
    else:
        # För knappar/switchar: Ingen OK/Fail-tolkning
        return True


def get_status_text(index, gpio_state):
    """
    Generera statustexten för en DI-ingång
    
    Returns:
        ('OK', '⚠️  LARM', '⚠️  AKTIV', etc.)
    """
    config = get_di_info(index)
    
    if config['high_means'] == 'ALARM':
        # NC-kontakter och övervakningar
        return '⚠️  LARM' if gpio_state else 'OK'
    elif config['high_means'] == 'PRESSED':
        # Knappar
        return '⚠️  TRYCKT' if gpio_state else 'OK'
    elif config['high_means'] == 'ACTIVE':
        # Switchar/lägen
        return '⚠️  AKTIV' if gpio_state else 'OK'
    else:
        return 'OK'
