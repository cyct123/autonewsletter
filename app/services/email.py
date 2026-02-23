import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.utils.logger import logger


async def send_email(to_address: str, content: str, title: str = "每周Newsletter") -> dict:
    """Send email via SMTP"""
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_pass]):
        logger.warning("email_not_configured")
        return {"ok": False, "error": "Email not configured"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = settings.smtp_user
        msg["To"] = to_address

        # Attach HTML content
        html_part = MIMEText(content, "html", "utf-8")
        msg.attach(html_part)

        # Send email
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)

        logger.info("email_sent", to=to_address)
        return {"ok": True}

    except Exception as e:
        logger.error("email_failed", to=to_address, error=str(e))
        return {"ok": False, "error": str(e)}
