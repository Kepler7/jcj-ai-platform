import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def send_password_reset_email(*, to_email: str, reset_link: str) -> None:
    # Si no está configurado SMTP, no truena (útil para dev)
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[DEV] SMTP not configured. Reset link for {to_email}: {reset_link}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Reset your password"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        "Hi!\n\n"
        "We received a request to reset your password.\n\n"
        f"Reset link (expires soon):\n{reset_link}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
