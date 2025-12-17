#!/usr/bin/env python3
"""
Interactive SMTP configuration setup script for fotbollsplan-bevattning.

This script guides the user through setting up SMTP email configuration,
validates the input, saves it to a .env file, and tests the configuration
by sending a test email.
"""

import os
import sys
import smtplib
import ssl
import re
from email.message import EmailMessage
from getpass import getpass
from pathlib import Path
from typing import Tuple, Optional


# Constants
DEFAULT_API_KEY = 'byt-mig'
DEFAULT_SMTP_HOST = 'smtp.gmail.com'
DEFAULT_SMTP_PORT = '587'
DEFAULT_SMTP_TIMEOUT = '10'
DEFAULT_MODBUS_HOST = '127.0.0.1'
DEFAULT_MODBUS_PORT = '502'
DEFAULT_MODBUS_UNIT = '1'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"✓ {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"✗ {text}", file=sys.stderr)


def print_info(text: str) -> None:
    """Print an informational message."""
    print(f"ℹ {text}")


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_port(port_str: str) -> Tuple[bool, int]:
    """Validate port number (1-65535)."""
    try:
        port = int(port_str)
        if 1 <= port <= 65535:
            return True, port
        return False, 0
    except ValueError:
        return False, 0


def get_input(prompt: str, default: str = None, validator=None) -> str:
    """Get user input with optional default and validation."""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                user_input = default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if not user_input:
            print_error("Input cannot be empty. Please try again.")
            continue
        
        if validator:
            if validator(user_input):
                return user_input
            else:
                print_error("Invalid input. Please try again.")
                continue
        
        return user_input


def get_yes_no(prompt: str, default: bool = False) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print_error("Please answer 'y' or 'n'.")


def test_smtp_connection(smtp_host: str, smtp_port: int, smtp_user: Optional[str], 
                         smtp_pass: Optional[str], smtp_from: str, smtp_to: str,
                         use_2fa: bool) -> Tuple[bool, str]:
    """
    Test SMTP configuration by sending a test email.
    
    Authentication is optional - only performed if both smtp_user and smtp_pass are provided.
    
    Returns: (success: bool, message: str)
    """
    print_info("Testing SMTP connection...")
    
    msg = EmailMessage()
    msg["Subject"] = "Fotbollsplan-bevattning: SMTP Configuration Test"
    msg["From"] = smtp_from
    msg["To"] = smtp_to
    msg.set_content(
        "This is a test email from the fotbollsplan-bevattning setup script.\n\n"
        "Your SMTP configuration is working correctly!\n\n"
        f"SMTP Server: {smtp_host}:{smtp_port}\n"
        f"From: {smtp_from}\n"
        f"To: {smtp_to}\n"
        f"2FA Enabled: {use_2fa}\n"
    )
    
    context = ssl.create_default_context()
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.set_debuglevel(0)  # Set to 1 for debugging
            server.starttls(context=context)
            
            # Only login if credentials are provided
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            
            server.send_message(msg)
            
        return True, "Test email sent successfully!"
    
    except smtplib.SMTPAuthenticationError as e:
        return False, f"Authentication failed: {e}. Check your email and password."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def load_existing_env(env_file: Path) -> dict:
    """Load existing environment variables from .env file."""
    env_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
    return env_vars


def save_env_file(env_file: Path, env_vars: dict) -> None:
    """Save environment variables to .env file."""
    with open(env_file, 'w') as f:
        f.write("# Fotbollsplan-bevattning Environment Configuration\n")
        f.write("# Generated by install.py\n\n")
        
        # Group related variables
        f.write("# API Configuration\n")
        for key in ['API_KEY', 'MODBUS_HOST', 'MODBUS_PORT', 'MODBUS_UNIT', 'API_URL']:
            if key in env_vars:
                f.write(f"{key}={env_vars[key]}\n")
        
        f.write("\n# SMTP Configuration\n")
        smtp_keys = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 
                     'SMTP_FROM', 'SMTP_TO', 'SMTP_TIMEOUT']
        for key in smtp_keys:
            if key in env_vars:
                f.write(f"{key}={env_vars[key]}\n")
        
        f.write("\n# Healthcheck Configuration\n")
        healthcheck_keys = ['HEALTHCHECK_TIMEOUT', 'HEALTHCHECK_RETRIES']
        for key in healthcheck_keys:
            if key in env_vars:
                f.write(f"{key}={env_vars[key]}\n")
        
        # Add any other remaining variables
        written_keys = set(['API_KEY', 'MODBUS_HOST', 'MODBUS_PORT', 'MODBUS_UNIT', 
                           'API_URL'] + smtp_keys + healthcheck_keys)
        other_vars = {k: v for k, v in env_vars.items() if k not in written_keys}
        if other_vars:
            f.write("\n# Other Configuration\n")
            for key, value in other_vars.items():
                f.write(f"{key}={value}\n")


def main() -> int:
    """Main installation script."""
    print_header("Fotbollsplan-bevattning SMTP Configuration Setup")
    
    print("This script will help you configure SMTP email settings.")
    print("You'll need:")
    print("  • SMTP server address (e.g., smtp.gmail.com)")
    print("  • SMTP port (usually 587 for TLS)")
    print("  • Email address and password")
    print("  • Recipient email address(es)\n")
    
    # Determine .env file location
    script_dir = Path(__file__).parent.resolve()
    env_file = script_dir / "api_.env"
    
    # Check if .env file already exists
    if env_file.exists():
        print_info(f"Found existing configuration file: {env_file}")
        if not get_yes_no("Do you want to update it?", default=True):
            print("Setup cancelled.")
            return 0
        existing_vars = load_existing_env(env_file)
    else:
        print_info(f"Will create new configuration file: {env_file}")
        # Load from example file if it exists
        example_file = script_dir / "api_.env.example"
        if example_file.exists():
            existing_vars = load_existing_env(example_file)
        else:
            existing_vars = {}
    
    print_header("SMTP Server Configuration")
    
    # Get SMTP server
    default_smtp_host = existing_vars.get('SMTP_HOST', DEFAULT_SMTP_HOST)
    smtp_host = get_input("SMTP server address", default=default_smtp_host)
    
    # Get SMTP port
    default_smtp_port = existing_vars.get('SMTP_PORT', DEFAULT_SMTP_PORT)
    while True:
        port_str = get_input("SMTP port", default=default_smtp_port)
        valid, smtp_port = validate_port(port_str)
        if valid:
            break
        print_error("Invalid port number. Must be between 1 and 65535.")
    
    # Get email address
    default_email = existing_vars.get('SMTP_USER', '')
    smtp_user = get_input("Your email address", default=default_email or None, 
                         validator=validate_email)
    
    # Get password
    print_info("Enter your email password (input will be hidden)")
    smtp_pass = getpass("Password: ")
    while not smtp_pass:
        print_error("Password cannot be empty.")
        smtp_pass = getpass("Password: ")
    
    # Ask about 2FA
    use_2fa = get_yes_no("Are you using two-factor authentication (2FA)?", default=False)
    if use_2fa:
        # Provide generic 2FA guidance with specific example for Gmail
        if 'gmail' in smtp_host.lower():
            print_info("Note: For Gmail with 2FA, you need an 'App Password'.")
            print_info("Generate one at: https://myaccount.google.com/apppasswords")
        else:
            print_info("Note: With 2FA enabled, you may need an 'App Password' from your email provider.")
            print_info("Check your email provider's documentation for app-specific passwords.")
    
    # Get sender email (usually same as SMTP_USER)
    default_from = existing_vars.get('SMTP_FROM', smtp_user)
    smtp_from = get_input("Sender email address (From)", default=default_from,
                         validator=validate_email)
    
    # Get recipient email(s)
    default_to = existing_vars.get('SMTP_TO', smtp_user)
    print_info("Enter recipient email(s). Separate multiple emails with commas.")
    smtp_to = get_input("Recipient email address(es) (To)", default=default_to)
    
    # Validate recipient emails
    recipients = [email.strip() for email in smtp_to.split(',')]
    for recipient in recipients:
        if not validate_email(recipient):
            print_error(f"Invalid recipient email: {recipient}")
            return 1
    
    # SMTP timeout
    default_timeout = existing_vars.get('SMTP_TIMEOUT', DEFAULT_SMTP_TIMEOUT)
    smtp_timeout = get_input("SMTP timeout (seconds)", default=default_timeout)
    
    print_header("Configuration Summary")
    print(f"SMTP Server:    {smtp_host}:{smtp_port}")
    print(f"Email:          {smtp_user}")
    print(f"2FA Enabled:    {use_2fa}")
    print(f"From:           {smtp_from}")
    print(f"To:             {smtp_to}")
    print(f"Timeout:        {smtp_timeout}s")
    
    if not get_yes_no("\nDo you want to test this configuration?", default=True):
        print_info("Skipping SMTP test.")
    else:
        # Test SMTP connection
        success, message = test_smtp_connection(
            smtp_host, smtp_port, smtp_user, smtp_pass, 
            smtp_from, recipients[0], use_2fa
        )
        
        if success:
            print_success(message)
        else:
            print_error(message)
            if not get_yes_no("Do you want to save the configuration anyway?", default=False):
                print("Setup cancelled.")
                return 1
    
    # Save configuration
    print_header("Saving Configuration")
    
    # Update environment variables
    existing_vars['SMTP_HOST'] = smtp_host
    existing_vars['SMTP_PORT'] = str(smtp_port)
    existing_vars['SMTP_USER'] = smtp_user
    existing_vars['SMTP_PASS'] = smtp_pass
    existing_vars['SMTP_FROM'] = smtp_from
    existing_vars['SMTP_TO'] = smtp_to
    existing_vars['SMTP_TIMEOUT'] = smtp_timeout
    
    # Ensure API configuration exists
    if 'API_KEY' not in existing_vars:
        existing_vars['API_KEY'] = DEFAULT_API_KEY
    if 'MODBUS_HOST' not in existing_vars:
        existing_vars['MODBUS_HOST'] = DEFAULT_MODBUS_HOST
    if 'MODBUS_PORT' not in existing_vars:
        existing_vars['MODBUS_PORT'] = DEFAULT_MODBUS_PORT
    if 'MODBUS_UNIT' not in existing_vars:
        existing_vars['MODBUS_UNIT'] = DEFAULT_MODBUS_UNIT
    
    try:
        save_env_file(env_file, existing_vars)
        print_success(f"Configuration saved to: {env_file}")
        
        print_header("Setup Complete!")
        print("Your SMTP configuration has been saved.")
        print("\nNext steps:")
        print("  1. Update API_KEY in api_.env if you haven't already")
        print("  2. Test healthcheck: python3 healthcheck.py")
        print("  3. Start the API: uvicorn api_main:app --host 0.0.0.0 --port 8000")
        print("\nFor more information, see README.md")
        
        return 0
    
    except Exception as e:
        print_error(f"Failed to save configuration: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
