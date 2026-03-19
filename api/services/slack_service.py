"""
Slack notification service for the customer portal.

Posts lead and quote notifications to #inbound-channel via Slack Bot API.
Requires SLACK_BOT_TOKEN env var. Channel ID is hardcoded to #inbound-channel.
"""
import os
import logging

import httpx

logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
# Production: #inbound-channel
INBOUND_CHANNEL_ID = "C090UDK9CF5"
SLACK_API_URL = "https://slack.com/api/chat.postMessage"


def _fmt_currency(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.4f}"


async def _post_to_slack(text: str):
    """Post a message to #inbound-channel via Slack Bot API."""
    if not SLACK_BOT_TOKEN:
        logger.warning("SLACK_BOT_TOKEN not set — skipping Slack notification")
        logger.info(f"Slack message (dry run):\n{text}")
        return

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SLACK_API_URL,
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                json={
                    "channel": INBOUND_CHANNEL_ID,
                    "text": text,
                },
                timeout=10.0,
            )
            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Slack API error: {data.get('error', 'unknown')}")
            else:
                logger.info("Slack notification sent successfully")
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")


async def notify_slack_new_lead(lead_data: dict):
    """Notify Slack about a new lead."""
    text = (
        f":new: *New Lead Captured*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f":bust_in_silhouette: {lead_data.get('full_name', '')} — {lead_data.get('business_name', '')}\n"
        f":email: {lead_data.get('email', '')} | :phone: {lead_data.get('phone', '')}\n"
        f":moneybag: Annual Spend: {lead_data.get('annual_spend', '')}\n"
    )
    await _post_to_slack(text)


async def notify_slack_manager_request(lead_data: dict, quote_id: int, lead_id: int):
    """Notify Slack that a customer wants to speak with an account manager."""
    lead_url = f"https://calyx-quoting-portal.vercel.app/lead/{lead_id}"
    text = (
        f":speech_balloon: *New Quick Quote Completed*\n"
        f":bust_in_silhouette: {lead_data.get('full_name', '')} — {lead_data.get('business_name', '')}\n"
        f":email: {lead_data.get('email', '')} | :phone: {lead_data.get('phone', '')}\n"
        f"\n"
        f":mag: <{lead_url}|View Full Lead Details>\n"
        f"\n"
        f":rotating_light: *Please reach out to this customer ASAP.*"
    )
    await _post_to_slack(text)
