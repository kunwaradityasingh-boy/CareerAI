import os
import resend

from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from project root
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")


def send_email(to_email: str, subject: str, html_content: str) -> dict:
    """
    Send an email using the Resend API.
    """

    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not configured.")

    if not RESEND_FROM_EMAIL:
        raise RuntimeError("RESEND_FROM_EMAIL is not configured.")

    resend.api_key = RESEND_API_KEY

    try:
        response = resend.Emails.send(
            {
                "from": RESEND_FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
        )

        return {
            "success": True,
            "message_id": response.get("id"),
        }

    except Exception as error:
        import logging

        logger = logging.getLogger(__name__)

        logger.error(
            "Resend email delivery failed: %s",
            error,
        )

        raise RuntimeError(f"Email delivery failed: {error}") from error
