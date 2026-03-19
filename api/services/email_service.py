"""
Email service for sending PDF estimates to customers.

Uses Gmail API via OAuth2 (HTTPS, works on Railway).
Requires GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN env vars.
"""
import os
import base64
import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import httpx

logger = logging.getLogger(__name__)

GMAIL_USER = os.getenv("GMAIL_USER", "quotes@calyxcontainers.com")
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN", "")
REPLY_TO = "Calyx Containers Sales <sales@calyxcontainers.com>"


async def _get_access_token() -> str:
    """Exchange refresh token for a short-lived access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GMAIL_CLIENT_ID,
                "client_secret": GMAIL_CLIENT_SECRET,
                "refresh_token": GMAIL_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def send_estimate_email(
    to_email: str,
    customer_name: str,
    attachments: list[tuple[bytes, str]],  # (pdf_bytes, filename)
    primary_estimate_number: str,
) -> bool:
    """Send PDF estimate(s) to a customer via Gmail API."""
    if not all([GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN]):
        logger.warning("Gmail OAuth2 credentials not set — skipping email")
        return False

    first_name = customer_name.split()[0] if customer_name else "there"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background-color: #ffffff; padding: 24px; text-align: center; border-bottom: 3px solid #0033A1;">
        <img
          src="https://calyx-quoting-portal.vercel.app/calyx-logo.svg"
          alt="Calyx Containers"
          width="200"
          style="display: block; margin: 0 auto;"
        />
      </div>
      <div style="padding: 32px 24px;">
        <p style="font-size: 16px; color: #1a1a1a;">Hi {first_name},</p>
        <p style="font-size: 14px; color: #4a4a4a; line-height: 1.6;">
          Thank you for using our instant quoting tool! Your packaging estimate
          is attached to this email for your records.
        </p>
        <p style="font-size: 14px; color: #4a4a4a; line-height: 1.6;">
          This estimate is for budgetary and planning purposes. Final pricing
          will be confirmed once artwork is received and reviewed by our team.
        </p>
        <p style="font-size: 14px; color: #4a4a4a; line-height: 1.6;">
          Have questions or ready to move forward? <strong>Simply reply to this
          email</strong> and one of our account managers will be in touch shortly.
        </p>
        <p style="font-size: 14px; color: #1a1a1a; margin-top: 24px;">
          Best regards,<br/>
          <strong>The Calyx Containers Team</strong><br/>
          <span style="color: #6b7280; font-size: 13px;">(724) 303-7481</span>
        </p>
      </div>
      <div style="background-color: #f3f4f6; padding: 16px 24px; text-align: center;">
        <p style="font-size: 12px; color: #6b7280; margin: 0;">
          Calyx Containers &middot; 1991 Parkway Blvd &middot; West Valley City, UT 84119
        </p>
      </div>
    </div>
    """

    try:
        msg = MIMEMultipart()
        msg["From"] = f"Calyx Containers <{GMAIL_USER}>"
        msg["To"] = to_email
        msg["Reply-To"] = REPLY_TO
        msg["Subject"] = f"Your Calyx Containers Estimate ({primary_estimate_number})"
        msg.attach(MIMEText(html_body, "html"))

        for pdf_bytes, filename in attachments:
            part = MIMEApplication(pdf_bytes, Name=filename)
            part["Content-Disposition"] = f'attachment; filename="{filename}"'
            msg.attach(part)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        access_token = await _get_access_token()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/{GMAIL_USER}/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw},
            )
            resp.raise_for_status()

        logger.info(f"Estimate email sent to {to_email} ({primary_estimate_number})")
        return True
    except Exception as e:
        logger.error(f"Failed to send estimate email to {to_email}: {e}")
        return False
