#!/usr/bin/env python3
"""
email_test.py - SMTP Test Script för Fotbollsplan Bevattning System 2.0

Detta script testar e-postnotifieringar genom att:
- Ladda SMTP-konfiguration från api_.env
- Skicka grundläggande test-mail
- Skicka simulerat larm-mail
- Verifiera att healthcheck.py existerar och fungerar

SMTP-variabler från .env:
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
- SMTP_FROM, SMTP_TO

Användning:
    python3 email_test.py
    python3 email_test.py --send-alarm-test
    python3 email_test.py --smtp-host smtp.example.com --smtp-port 587

Tips:
- För Gmail med 2FA: Använd App Password från https://myaccount.google.com/apppasswords
- Kontrollera spam-mappen om mail inte kommer fram
- Kontrollera firewall och att port 587/465 är öppen
"""

import argparse
import os
import smtplib
import ssl
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv saknas. Installera: pip install python-dotenv")
    sys.exit(1)

# Färgkoder
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def print_header(text: str) -> None:
    """Print formaterad header."""
    print(f"\n{BLUE}{'=' * 70}{NC}")
    print(f"{BLUE}  {text}{NC}")
    print(f"{BLUE}{'=' * 70}{NC}\n")


def print_success(text: str) -> None:
    """Print success-meddelande."""
    print(f"{GREEN}✓{NC} {text}")


def print_error(text: str) -> None:
    """Print error-meddelande."""
    print(f"{RED}✗{NC} {text}")


def print_warning(text: str) -> None:
    """Print warning-meddelande."""
    print(f"{YELLOW}⚠{NC} {text}")


def print_info(text: str) -> None:
    """Print info-meddelande."""
    print(f"{BLUE}ℹ{NC} {text}")


def load_smtp_config(env_file: str = "api_.env") -> dict:
    """
    Ladda SMTP-konfiguration från .env-fil.
    
    Returns:
        Dict med SMTP-konfiguration
    """
    print_info(f"Laddar konfiguration från {env_file}...")
    
    if not Path(env_file).exists():
        print_warning(f"{env_file} hittades inte")
        return {}
    
    load_dotenv(env_file)
    
    config = {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASS"),
        "from": os.getenv("SMTP_FROM"),
        "to": os.getenv("SMTP_TO"),
        "timeout": int(os.getenv("SMTP_TIMEOUT", "10")),
    }
    
    # Validera konfiguration
    missing = []
    for key in ["host", "user", "password", "to"]:
        if not config.get(key):
            missing.append(key.upper())
    
    if missing:
        print_error(f"SMTP-konfiguration saknas: {', '.join(missing)}")
        print_info("Konfigurera i api_.env eller använd command-line arguments")
        return {}
    
    # Använd user som from om from inte är satt
    if not config["from"]:
        config["from"] = config["user"]
    
    print_success("SMTP-konfiguration laddad")
    print(f"  Host: {config['host']}:{config['port']}")
    print(f"  User: {config['user']}")
    print(f"  From: {config['from']}")
    print(f"  To: {config['to']}")
    
    return config


def send_email(config: dict, subject: str, body: str) -> bool:
    """
    Skicka e-post via SMTP.
    
    Args:
        config: SMTP-konfiguration
        subject: E-post ämne
        body: E-post innehåll
    
    Returns:
        True om e-post skickades, False vid fel
    """
    try:
        # Skapa meddelande
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = config["from"]
        msg["To"] = config["to"]
        msg.set_content(body)
        
        # Skapa SSL-kontext
        context = ssl.create_default_context()
        
        # Anslut och skicka
        print_info(f"Ansluter till SMTP-server: {config['host']}:{config['port']}")
        
        with smtplib.SMTP(config["host"], config["port"], timeout=config["timeout"]) as server:
            # Aktivera TLS
            server.starttls(context=context)
            print_success("TLS aktiverat")
            
            # Logga in
            if config["user"] and config["password"]:
                server.login(config["user"], config["password"])
                print_success("Inloggning lyckades")
            
            # Skicka meddelande
            server.send_message(msg)
            print_success(f"E-post skickat till {config['to']}")
        
        return True
    
    except smtplib.SMTPAuthenticationError as e:
        print_error(f"Autentiseringsfel: {e}")
        print_info("Kontrollera användarnamn och lösenord")
        print_info("För Gmail med 2FA: Använd App Password från https://myaccount.google.com/apppasswords")
        return False
    
    except smtplib.SMTPException as e:
        print_error(f"SMTP-fel: {e}")
        return False
    
    except Exception as e:
        print_error(f"Oväntat fel: {e}")
        return False


def send_basic_test(config: dict) -> bool:
    """
    Skicka grundläggande test-mail.
    
    Returns:
        True om test lyckades, False vid fel
    """
    print_header("Grundläggande E-post Test")
    
    subject = "Fotbollsplan Bevattning - Test-mail"
    body = f"""Detta är ett test-mail från Fotbollsplan Bevattning System 2.0.

Om du ser detta meddelande fungerar SMTP-konfigurationen korrekt.

Systeminfo:
- Tidpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Host: {config['host']}:{config['port']}
- From: {config['from']}

Nästa steg:
1. Kontrollera att du fick detta mail i inkorgen (kolla spam-mappen!)
2. Kör email_test.py --send-alarm-test för att testa larm-meddelanden

Med vänlig hälsning,
Fotbollsplan Bevattning System
"""
    
    return send_email(config, subject, body)


def send_alarm_test(config: dict) -> bool:
    """
    Skicka simulerat larm-mail.
    
    Returns:
        True om test lyckades, False vid fel
    """
    print_header("Larm-meddelande Test")
    
    subject = "🚨 LARM - Fotbollsplan Bevattning - TEST"
    body = f"""DETTA ÄR ETT TEST-LARM

Ett simulerat larm har triggats från bevattningssystemet.

Larmtyp: TEST - Motorskydd utlöst (simulerat)
Tidpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Zon: Zon 3 (simulerat)
Status: Bevattning stoppad

Detaljer:
- Motorskydd (DI10) har utlöst
- Pumpen är automatiskt stoppad
- Systemet väntar på manuell återställning

Åtgärder:
1. Kontrollera motorskydd Q1 fysiskt
2. Kontrollera att pumpen inte är blockerad
3. Återställ motorskydd
4. Tryck på RESET-knappen på PLC

Detta var ett TEST-LARM. Om du får detta meddelande fungerar 
larm-notifieringarna korrekt.

OBS: Riktiga larm kommer att ha liknande format men utan "TEST" i ämnesraden.

Med vänlig hälsning,
Fotbollsplan Bevattning System
"""
    
    return send_email(config, subject, body)


def verify_healthcheck() -> bool:
    """
    Verifiera att healthcheck.py existerar och fungerar.
    
    Returns:
        True om healthcheck fungerar, False vid fel
    """
    print_header("Healthcheck Verifiering")
    
    healthcheck_path = Path("healthcheck.py")
    
    if not healthcheck_path.exists():
        print_error("healthcheck.py hittades inte")
        print_info("Healthcheck används för att övervaka systemet och skicka larm")
        return False
    
    print_success("healthcheck.py hittades")
    
    # Kolla att healthcheck kan köras
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "healthcheck.py", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 or "usage" in result.stdout.lower() or "usage" in result.stderr.lower():
            print_success("healthcheck.py är körbar")
            print_info("healthcheck.py används för att övervaka API och skicka larm vid problem")
            print_info("Kör healthcheck.py manuellt för att testa fullständig larm-funktionalitet")
            return True
        else:
            print_warning("healthcheck.py gav oväntat resultat")
            return False
    
    except Exception as e:
        print_error(f"Kunde inte verifiera healthcheck.py: {e}")
        return False


def main():
    """Main-funktion."""
    parser = argparse.ArgumentParser(
        description="E-post test för Fotbollsplan Bevattning System 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  python3 email_test.py
  python3 email_test.py --send-alarm-test
  python3 email_test.py --smtp-host smtp.gmail.com --smtp-port 587

Tips:
  - För Gmail med 2FA: Använd App Password
  - Kontrollera spam-mappen om mail inte kommer fram
  - Kontrollera firewall och att port 587/465 är öppen
        """
    )
    
    parser.add_argument("--send-alarm-test", action="store_true",
                       help="Skicka simulerat larm-mail")
    parser.add_argument("--smtp-host", help="SMTP host (override .env)")
    parser.add_argument("--smtp-port", type=int, help="SMTP port (override .env)")
    parser.add_argument("--smtp-user", help="SMTP user (override .env)")
    parser.add_argument("--smtp-pass", help="SMTP password (override .env)")
    parser.add_argument("--smtp-from", help="From address (override .env)")
    parser.add_argument("--smtp-to", help="To address (override .env)")
    parser.add_argument("--env-file", default="api_.env",
                       help="Path till .env-fil (default: api_.env)")
    
    args = parser.parse_args()
    
    # Banner
    print_header("Fotbollsplan Bevattning System 2.0 - E-post Test")
    
    # Ladda konfiguration
    config = load_smtp_config(args.env_file)
    
    # Override med command-line arguments
    if args.smtp_host:
        config["host"] = args.smtp_host
    if args.smtp_port:
        config["port"] = args.smtp_port
    if args.smtp_user:
        config["user"] = args.smtp_user
    if args.smtp_pass:
        config["password"] = args.smtp_pass
    if args.smtp_from:
        config["from"] = args.smtp_from
    if args.smtp_to:
        config["to"] = args.smtp_to
    
    # Validera konfiguration
    if not config or not config.get("host"):
        print_error("SMTP-konfiguration saknas eller ofullständig")
        print_info("Konfigurera i api_.env eller använd command-line arguments")
        return 1
    
    success = True
    
    # Grundläggande test
    if not send_basic_test(config):
        success = False
    
    # Larm-test (valfritt)
    if args.send_alarm_test:
        print()
        if not send_alarm_test(config):
            success = False
    
    # Verifiera healthcheck
    print()
    if not verify_healthcheck():
        success = False
    
    # Sammanfattning
    print_header("Sammanfattning")
    
    if success:
        print_success("Alla e-post-tester lyckades!")
        print()
        print_info("Kontrollera din inkorg (och spam-mapp) för test-mail")
        
        if not args.send_alarm_test:
            print()
            print_info("Kör med --send-alarm-test för att testa larm-meddelanden")
    else:
        print_error("Ett eller flera e-post-tester misslyckades")
        print()
        print_info("Felsökning:")
        print("  1. Kontrollera SMTP-inställningar i api_.env")
        print("  2. För Gmail: Använd App Password om 2FA är aktiverat")
        print("  3. Kontrollera firewall och nätverksanslutning")
        print("  4. Testa manuellt: telnet smtp.gmail.com 587")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
