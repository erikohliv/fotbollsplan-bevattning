"""
Digital Input Configuration
Definierar DI‑konfiguration och tolkning för systemet.

Systemet använder software pull-up (GPIO.PUD_UP) vilket ger Active‑Low:
- Sluten krets → dras till jord → GPIO = LOW (0)
- Öppen krets → pull‑up drar upp → GPIO = HIGH (1)

Tolkning som används här:
- NC (Normally Closed, säkerhetskontakter): LOW = OK, HIGH = ALARM
- NO (Normally Open, knappar): HIGH = INAKTIV, LOW = AKTIV/TRYCKT
"""

# DI‑konfiguration: index 0-11 motsvarar DI1-DI12
DI_CONFIG = {
    # NO‑knappar/switchar (Active‑Low): HIGH = INAKTIV, LOW = PRESSED/ACTIVE
    0: {'name': 'Stoppknapp S202', 'type': 'NO', 'high_means': 'INACTIVE', 'critical': False},
    1: {'name': 'Startknapp S201', 'type': 'NO', 'high_means': 'INACTIVE', 'critical': False},
    3: {'name': 'Resetknapp S203', 'type': 'NO', 'high_means': 'INACTIVE', 'critical': False},
    4: {'name': 'Auto-läge S204', 'type': 'NO', 'high_means': 'INACTIVE', 'critical': False, 'note': '⚙️  Återfjädrande vred, PLC latchar läge'},
    5: {'name': 'Manuell-läge S204', 'type': 'NO', 'high_means': 'INACTIVE', 'critical': False, 'note': '⚙️  Återfjädrande vred, PLC latchar läge'},
    6: {'name': 'Flödesvakt', 'type': 'NO', 'high_means': 'ALARM', 'critical': False},
    8: {'name': 'Tryckvakt', 'type': 'NO', 'high_means': 'ALARM', 'critical': False},

    # NC‑kontakter (Fail‑safe): LOW = OK, HIGH = ALARM
    2: {'name': 'Nödstopp S205', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': 'PLC blockerar (BlockReason=4). Måste vridas upp fysiskt!'},
    7: {'name': 'Mjukstartare Fault', 'type': 'NC', 'high_means': 'ALARM', 'critical': False, 'note': '🟡 PLC stoppar pump (BlockReason=8, auto-reset)'},
    9: {'name': 'Motorskydd Q1', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': 'PLC stoppar pump (BlockReason=7). Måste resetas på Q1!'},
    10: {'name': '24VDC Säkring', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': '⚠️  Ingen PLC-hantering. Säkring måste resetas/bytas!'},
    11: {'name': '24VAC Säkring', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': '[EJ INSTALLERAD] Säkring måste resetas/bytas vid fel'},
}


def get_di_info(index):
    """Hämta info för en DI‑ingång (0-11)."""
    return DI_CONFIG.get(index, {
        'name': f'DI{index+1}',
        'type': 'NO',
        'high_means': 'INACTIVE',
        'critical': False,
        'note': None
    })


def is_alarm(index, gpio_state):
    """
    Avgör om en DI‑ingång är i larmläge (returnerar True vid larm).

    Active‑Low‑regler:
    - NC: HIGH (True) = ALARM
    - NO med high_means='ALARM': LOW (False) = ALARM
    - NO knappar: LOW (False) = PRESSED/ACTIVE
    """
    config = get_di_info(index)
    gpio_bool = bool(gpio_state)

    # NC: HIGH = ALARM
    if config.get('type') == 'NC':
        return gpio_bool

    # NO sensors where ALARM is signalled by active (LOW)
    if config.get('type') == 'NO' and config.get('high_means') == 'ALARM':
        return not gpio_bool

    # NO buttons: LOW = pressed (can be considered active)
    if config.get('type') == 'NO' and config.get('high_means') == 'INACTIVE':
        return not gpio_bool

    return False


def is_di_ok(index, gpio_state):
    """
    Returnerar True om DI är i OK‑tillstånd (säkerhetsbedömning).
    """
    config = get_di_info(index)
    gpio_bool = bool(gpio_state)

    # NC: LOW = OK
    if config.get('type') == 'NC':
        return not gpio_bool

    # NO sensors with ALARM meaning: HIGH = OK
    if config.get('type') == 'NO' and config.get('high_means') == 'ALARM':
        return gpio_bool

    # NO buttons/switches considered OK when not pressed (HIGH)
    return True


def get_status_text(index, gpio_state):
    """
    Generera statustext för UI utifrån Active‑Low‑logik.
    """
    config = get_di_info(index)
    gpio_bool = bool(gpio_state)

    if is_alarm(index, gpio_state):
        return '⚠️  LARM'

    # Knappar / aktiva tillstånd
    if config.get('type') == 'NO' and config.get('high_means') == 'INACTIVE':
        return '⚠️  TRYCKT' if not gpio_bool else 'OK'
    if config.get('type') == 'NO' and config.get('high_means') == 'ALARM':
        return '⚠️  AKTIV' if not gpio_bool else 'OK'

    return 'OK'

