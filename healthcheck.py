#!/usr/bin/env python3
"""
Simple healthcheck: polls API /status and emails on failure.
Config via env:
- API_URL (default http://127.0.0.1:8000/status)
- API_KEY (required header)
- SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_TO (comma-separated)
"""
import os
import smtplib
import socket
import ssl
import sys
from email.message import EmailMessage
from datetime import datetime

try:
    import requests
    from requests import RequestException
except ImportError:
    requests = None
    RequestException = Exception


def send_mail(subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    if not host:
        return
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM", user or "healthcheck@localhost")
    recipients = [r.strip() for r in os.getenv("SMTP_TO", "").split(",") if r.strip()]
    if not recipients:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls(context=context)
            if user and pwd:
                server.login(user, pwd)
            server.send_message(msg)
    except Exception as e:
        print(f"[healthcheck] email send failed: {e}", file=sys.stderr)


def main() -> int:
    api_url = os.getenv("API_URL", "http://127.0.0.1:8000/status")
    api_key = os.getenv("API_KEY")
    if not api_key:
        msg = "[healthcheck] API_KEY is required"
        send_mail("Healthcheck failed", msg)
        print(msg, file=sys.stderr)
        return 1
    host = socket.gethostname()
    if requests is None:
        msg = f"[healthcheck] requests not installed on {host}"
        send_mail("Healthcheck failed", msg)
        print(msg, file=sys.stderr)
        return 1
    try:
        resp = requests.get(api_url, headers={"X-API-Key": api_key}, timeout=5)
        ok = resp.status_code == 200
        if ok:
            try:
                payload = resp.json()
            except ValueError:
                payload = {"error": "invalid json", "text": resp.text}
        else:
            payload = {}
    except RequestException as e:
        ok = False
        payload = {"error": str(e)}

    if ok:
        print(f"{datetime.now().isoformat()} OK {payload}")
        return 0

    body = (
        f"Healthcheck failed on {host}\n"
        f"URL: {api_url}\n"
        f"Payload: {payload}\n"
        f"Time: {datetime.now().isoformat()}"
    )
    send_mail("Healthcheck failed", body)
    print(body, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
