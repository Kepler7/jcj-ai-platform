import os
import resend

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "IHUI <onboarding@resend.dev>")


def send_password_reset_email(*, to_email: str, reset_link: str) -> None:
    """
    Envía el correo de recuperación de contraseña usando Resend por API HTTP.

    Importante:
    - No usa SMTP, porque DigitalOcean puede bloquear puertos SMTP como 587.
    - Usa HTTPS, que ya comprobamos que sí funciona desde la Droplet.
    - Si no hay RESEND_API_KEY, no truena; solo imprime el link para desarrollo.
    """

    if not RESEND_API_KEY:
        print(
            f"[DEV] RESEND_API_KEY not configured. Reset link for {to_email}: {reset_link}"
        )
        return

    resend.api_key = RESEND_API_KEY

    params: resend.Emails.SendParams = {
        "from": RESEND_FROM,
        "to": [to_email],
        "subject": "Reset your IHUI password",
        "text": (
            "Hi!\n\n"
            "We received a request to reset your IHUI password.\n\n"
            f"Reset link (expires soon):\n{reset_link}\n\n"
            "If you did not request this, you can ignore this email.\n"
        ),
    }

    resend.Emails.send(params)
