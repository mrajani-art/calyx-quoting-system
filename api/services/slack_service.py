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
# Testing: DM Cory directly. Switch to C090UDK9CF5 for #inbound-channel in production.
INBOUND_CHANNEL_ID = "U04P18H18B1"
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


async def notify_slack_quote(lead_data: dict, quote_data: dict):
    """Notify Slack about a completed quote with pricing details."""
    specs = quote_data.get("specifications", {})
    dims = f"{specs.get('width', '?')}×{specs.get('height', '?')}×{specs.get('gusset', '?')}\""
    seal_type = specs.get("seal_type", "")
    substrate = specs.get("substrate", "")
    finish = specs.get("finish", "")

    # Extract unit prices at the first tier for each method
    def _first_unit_price(method_data: dict | None) -> str:
        if not method_data:
            return "N/A"
        tiers = method_data.get("tiers", [])
        if not tiers:
            return "N/A"
        return _fmt_currency(tiers[0].get("unit_price"))

    digital_price = _first_unit_price(quote_data.get("digital"))
    flexo_price = _first_unit_price(quote_data.get("flexographic"))
    air_price = _first_unit_price(quote_data.get("international_air"))
    ocean_price = _first_unit_price(quote_data.get("international_ocean"))

    qtys = specs.get("quantities", [])
    qty_str = ", ".join(f"{q:,}" for q in qtys) if qtys else "N/A"

    text = (
        f":new: *New Quote Request*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f":bust_in_silhouette: Lead: {lead_data.get('lead_id', 'unknown')}\n"
        f"\n"
        f":package: Bag: {dims} {seal_type}\n"
        f":art: {substrate}, {finish}\n"
        f":bar_chart: Qty tiers: {qty_str}\n"
        f"\n"
        f":dollar: Digital: {digital_price}/unit\n"
        f":dollar: Flexo: {flexo_price}/unit\n"
        f":dollar: Intl Air: {air_price}/unit\n"
        f":dollar: Intl Ocean: {ocean_price}/unit\n"
    )
    await _post_to_slack(text)


async def notify_slack_manager_request(lead_data: dict, quote_id: str):
    """Notify Slack that a customer wants to speak with an account manager."""
    text = (
        f":speech_balloon: *Account Manager Requested*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f":bust_in_silhouette: {lead_data.get('full_name', '')} — {lead_data.get('business_name', '')}\n"
        f":email: {lead_data.get('email', '')} | :phone: {lead_data.get('phone', '')}\n"
        f":moneybag: Annual Spend: {lead_data.get('annual_spend', '')}\n"
        f":page_facing_up: Quote ID: {quote_id}\n"
        f"\n"
        f":rotating_light: *Please reach out to this customer ASAP.*"
    )
    await _post_to_slack(text)
