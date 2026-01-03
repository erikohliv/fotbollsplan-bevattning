#!/usr/bin/env python3
"""
Local Mode Monitor - Övervakar lokalt läge och skickar e-postvarning efter 24 timmar

Körs som en bakgrundstjänst och kontrollerar regelbundet om systemet är i lokalt läge.
Om systemet varit i lokalt läge i 24 timmar, skickas en e-postvarning.

Konfiguration via environment-variabler (api_.env):
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_TO
- MODBUS_HOST, MODBUS_PORT, MODBUS_UNIT
- LOCAL_MODE_CHECK_INTERVAL (sekunder, default 300 = 5 minuter)
- LOCAL_MODE_WARNING_HOURS (timmar, default 24)
"""

import os
import time
import logging
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv

try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client.sync import ModbusTcpClient
    except ImportError:
        ModbusTcpClient = None

# Ladda environment-variabler
load_dotenv("api_.env")

# Konfiguration
MODBUS_HOST = os.getenv('MODBUS_HOST', '127.0.0.1')
MODBUS_PORT = int(os.getenv('MODBUS_PORT', '502'))
MODBUS_UNIT = int(os.getenv('MODBUS_UNIT', '1'))
MW_MODE = 100  # Mode switch register

CHECK_INTERVAL = int(os.getenv('LOCAL_MODE_CHECK_INTERVAL', '300'))  # 5 minuter
WARNING_HOURS = int(os.getenv('LOCAL_MODE_WARNING_HOURS', '24'))  # 24 timmar

# SMTP-konfiguration
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
SMTP_FROM = os.getenv('SMTP_FROM', SMTP_USER)
SMTP_TO = os.getenv('SMTP_TO')

# State file för att spara när lokalt läge aktiverades
STATE_FILE = Path.home() / '.local_mode_state.json'

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('local_mode_monitor')


def load_state():
    """Ladda state från fil"""
    try:
        if STATE_FILE.exists():
            import json
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                if 'local_mode_started' in data:
                    return datetime.fromisoformat(data['local_mode_started'])
    except Exception as e:
        logger.debug(f"Could not load state: {e}")
    return None


def save_state(local_mode_started: datetime):
    """Spara state till fil"""
    try:
        import json
        with open(STATE_FILE, 'w') as f:
            json.dump({
                'local_mode_started': local_mode_started.isoformat()
            }, f)
    except Exception as e:
        logger.error(f"Could not save state: {e}")


def clear_state():
    """Rensa state-fil"""
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except Exception as e:
        logger.debug(f"Could not clear state: {e}")


def read_mode_switch():
    """Läs mode switch från PLC"""
    try:
        client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
        client.connect()
        
        result = client.read_holding_registers(MW_MODE, 1, device_id=MODBUS_UNIT)
        
        if result and not result.isError():
            mode = result.registers[0] if result.registers else 2
            client.close()
            return mode
        
        client.close()
        return None
    except Exception as e:
        logger.debug(f"Could not read mode switch: {e}")
        return None


def send_email_warning():
    """Skicka e-postvarning om lokalt läge"""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_TO]):
        logger.warning("SMTP-konfiguration saknas, kan inte skicka e-post")
        return False
    
    try:
        msg = EmailMessage()
        msg["Subject"] = "⚠️ VARNING: Bevattningssystem i lokalt läge i 24 timmar"
        msg["From"] = SMTP_FROM
        msg["To"] = SMTP_TO
        msg.set_content(f"""
VARNING: Bevattningssystem i lokalt läge

Systemet har varit i lokalt läge i {WARNING_HOURS} timmar.

Detta innebär att:
- Fjärrkommandon via API/webb kan fortfarande fungera
- Systemet kan ha fastnat i lokalt läge om du glömt att växla tillbaka

ÅTGÄRD:
1. Kontrollera fysisk switch (MW100) på PLC
2. Växla tillbaka till fjärrläge via webbgränssnitt eller fysisk switch
3. Verifiera att systemet fungerar normalt

Tidpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

System: Fotbollsplan Bevattning
""")
        
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        logger.info(f"E-postvarning skickad till {SMTP_TO}")
        return True
    except Exception as e:
        logger.error(f"Kunde inte skicka e-post: {e}")
        return False


def main():
    """Huvudloop för övervakning"""
    logger.info("Local Mode Monitor startar...")
    logger.info(f"Kontrollerar var {CHECK_INTERVAL} sekunder")
    logger.info(f"Varning efter {WARNING_HOURS} timmar i lokalt läge")
    
    if not SMTP_HOST:
        logger.warning("SMTP-konfiguration saknas - e-postvarningar kommer inte fungera")
    
    last_email_sent = None
    
    while True:
        try:
            mode = read_mode_switch()
            
            if mode == 1:  # Lokalt läge aktivt
                local_mode_started = load_state()
                
                if local_mode_started is None:
                    # Första gången vi detekterar lokalt läge
                    local_mode_started = datetime.now()
                    save_state(local_mode_started)
                    logger.info(f"Lokalt läge detekterat - startar övervakning: {local_mode_started}")
                else:
                    # Kontrollera om 24 timmar har passerat
                    elapsed = datetime.now() - local_mode_started
                    hours_elapsed = elapsed.total_seconds() / 3600
                    
                    if hours_elapsed >= WARNING_HOURS:
                        # Skicka e-post om vi inte redan skickat en idag
                        today = datetime.now().date()
                        if last_email_sent != today:
                            logger.warning(f"Lokalt läge aktivt i {hours_elapsed:.1f} timmar - skickar varning")
                            if send_email_warning():
                                last_email_sent = today
                        else:
                            logger.debug(f"E-post redan skickad idag ({today})")
                    else:
                        logger.debug(f"Lokalt läge aktivt i {hours_elapsed:.1f} timmar (varning vid {WARNING_HOURS}h)")
            
            elif mode == 2:  # Fjärrläge aktivt
                # Rensa state om vi är tillbaka i fjärrläge
                if load_state() is not None:
                    logger.info("Tillbaka i fjärrläge - rensar övervakning")
                    clear_state()
                    last_email_sent = None
            
            # Vänta innan nästa kontroll
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Avbryter...")
            break
        except Exception as e:
            logger.error(f"Fel i övervakningsloop: {e}")
            time.sleep(60)  # Vänta 1 minut vid fel


if __name__ == '__main__':
    main()

