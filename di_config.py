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

    # NC‑kontakter (Fail‑safe): 
    # DI3: Normalt (uppsläppt) = LOW, Utlöst (nedtryckt) = HIGH
    # DI8, DI10, DI11, DI12: Normalt = HIGH, Utlöst = LOW (inverterade)
    2: {'name': 'Nödstopp S205', 'type': 'NC', 'high_means': 'ALARM', 'critical': True, 'note': 'Normalt LOW (uppsläppt), LARM HIGH (nedtryckt)'},
    7: {'name': 'Mjukstartare Fault', 'type': 'NC', 'high_means': 'OK', 'critical': False, 'note': 'HIGH=OK (mjukstartare fungerar), LOW=LARM (fel - pump stoppas, auto-reset)'},
    9: {'name': 'Motorskydd Q1', 'type': 'NC', 'high_means': 'OK', 'critical': True, 'note': 'Normalt HIGH (ok), LARM LOW (utlöst)'},
    10: {'name': '24VDC Säkring', 'type': 'NC', 'high_means': 'OK', 'critical': True, 'note': 'Normalt HIGH (ok), LARM LOW (utlöst)'},
    11: {'name': '24VAC Säkring', 'type': 'NC', 'high_means': 'OK', 'critical': True, 'note': 'Normalt HIGH (ok), LARM LOW (utlöst) [EJ INSTALLERAD]'},
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

    Regler:
    - NC med high_means='ALARM': HIGH = ALARM, LOW = OK (t.ex. DI3 nödstopp)
    - NC med high_means='OK': LOW = ALARM, HIGH = OK (t.ex. DI8, DI10-12)
    - NO med high_means='ALARM': LOW = ALARM, HIGH = OK
    - NO knappar: ALDRIG LARM (bara aktiva/inaktiva)
    """
    config = get_di_info(index)
    gpio_bool = bool(gpio_state)

    # NC med high_means='ALARM': HIGH = LARM (t.ex. nödstopp)
    if config.get('type') == 'NC' and config.get('high_means') == 'ALARM':
        return gpio_bool  # HIGH = LARM
    
    # NC med high_means='OK': LOW = ALARM (t.ex. motorskydd, säkringar)
    if config.get('type') == 'NC' and config.get('high_means') == 'OK':
        return not gpio_bool  # LOW = LARM

    # NO sensors where ALARM is signalled by active (LOW)
    if config.get('type') == 'NO' and config.get('high_means') == 'ALARM':
        return not gpio_bool

    # NO buttons: ALDRIG LARM - bara aktiva eller inaktiva
    if config.get('type') == 'NO' and config.get('high_means') == 'INACTIVE':
        return False  # Knappar triggar aldrig larm

    return False


def is_di_ok(index, gpio_state):
    """
    Returnerar True om DI är i OK‑tillstånd (säkerhetsbedömning).
    """
    config = get_di_info(index)
    gpio_bool = bool(gpio_state)

    # NC med high_means='ALARM': LOW = OK (t.ex. nödstopp)
    if config.get('type') == 'NC' and config.get('high_means') == 'ALARM':
        return not gpio_bool  # LOW = OK
    
    # NC med high_means='OK': HIGH = OK (t.ex. motorskydd, säkringar)
    if config.get('type') == 'NC' and config.get('high_means') == 'OK':
        return gpio_bool  # HIGH = OK

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

    # Kolla larm FÖRST (för sensorer och NC-kontakter)
    if is_alarm(index, gpio_state):
        return '🚨 LARM'

    # Knappar (NO med INACTIVE) - visa om tryckt eller inte
    if config.get('type') == 'NO' and config.get('high_means') == 'INACTIVE':
        return '✓ TRYCKT' if not gpio_bool else 'OK'
    
    # Sensorer (NO med ALARM) - visa aktiv eller ok
    if config.get('type') == 'NO' and config.get('high_means') == 'ALARM':
        return '✓ AKTIV' if not gpio_bool else 'OK'

    return 'OK'

