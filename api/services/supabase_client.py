"""
Supabase client for the customer portal API.

Uses the service role key for full access to customer_leads and customer_quotes.
"""
import os
import logging
import uuid as uuid_lib
from typing import Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create the singleton Supabase client."""
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = create_client(url, key)
        logger.info("Supabase client initialized")
    return _client


def insert_lead(lead_data: dict) -> dict:
    """Insert a new lead and return the created row."""
    sb = get_supabase()
    result = sb.table("customer_leads").insert(lead_data).execute()
    return result.data[0] if result.data else {}


def insert_quote(quote_data: dict) -> dict:
    """Insert a new customer quote and return the created row."""
    sb = get_supabase()
    result = sb.table("customer_quotes").insert(quote_data).execute()
    return result.data[0] if result.data else {}


def update_quote(quote_id: str, updates: dict) -> dict:
    """Update a customer quote by ID."""
    sb = get_supabase()
    result = sb.table("customer_quotes").update(updates).eq("id", quote_id).execute()
    return result.data[0] if result.data else {}


def upload_file_to_storage(lead_id: str, file_name: str, file_content: bytes, content_type: str) -> tuple[str, str]:
    """Upload a file to Supabase Storage and return (storage_path, public_url)."""
    sb = get_supabase()
    file_uuid = str(uuid_lib.uuid4())
    safe_name = file_name.replace(" ", "_").replace("/", "_")
    storage_path = f"{lead_id}/{file_uuid}_{safe_name}"
    sb.storage.from_("customer-artwork").upload(
        path=storage_path,
        file=file_content,
        file_options={"content-type": content_type},
    )
    public_url = sb.storage.from_("customer-artwork").get_public_url(storage_path)
    return storage_path, public_url


def insert_file_record(file_data: dict) -> dict:
    """Insert a file tracking record into customer_files."""
    sb = get_supabase()
    result = sb.table("customer_files").insert(file_data).execute()
    return result.data[0] if result.data else {}


def get_files_for_lead(lead_id: str) -> list[dict]:
    """Get all files uploaded for a lead."""
    sb = get_supabase()
    result = sb.table("customer_files").select("*").eq("lead_id", lead_id).order("created_at", desc=True).execute()
    return result.data or []
