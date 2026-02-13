#!/usr/bin/env python3
"""
auto_ingest.py — Download new PDFs from Google Drive, skip duplicates, ingest to Supabase.
Called by the GitHub Actions workflow.
"""
import os
import sys
import json
import tempfile
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    SUPABASE_URL, SUPABASE_KEY,
    DAZPAK_FOLDER_ID, ROSS_FOLDER_ID
)
from src.data.supabase_client import get_client
from src.data.pdf_extraction import extract_dazpak_pdf, extract_ross_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_google_drive_service():
    """Build Google Drive API service from credentials."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    # First try: GOOGLE_CREDENTIALS_JSON env var (raw JSON string, used in GitHub Actions)
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)

    # Second try: GOOGLE_CREDENTIALS file path (used locally)
    creds_path = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_path and os.path.isfile(creds_path):
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)

    raise ValueError("Set GOOGLE_CREDENTIALS_JSON or GOOGLE_CREDENTIALS env var")


def list_pdfs_in_folder(drive_service, folder_id: str) -> list[dict]:
    """List all PDF files in a Google Drive folder. Returns list of {id, name}."""
    results = []
    page_token = None

    while True:
        response = drive_service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
            spaces="drive",
            fields="nextPageToken, files(id, name, modifiedTime)",
            pageToken=page_token,
            pageSize=100
        ).execute()

        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def download_pdf(drive_service, file_id: str, dest_path: str):
    """Download a single PDF from Google Drive."""
    from googleapiclient.http import MediaIoBaseDownload
    import io

    request = drive_service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def get_existing_fl_numbers(supabase, vendor: str) -> set[str]:
    """Query Supabase for all FL numbers already ingested for a vendor."""
    existing = set()
    try:
        offset = 0
        batch_size = 1000
        while True:
            response = (
                supabase.table("quotes")
                .select("fl_number")
                .eq("vendor", vendor)
                .range(offset, offset + batch_size - 1)
                .execute()
            )
            if not response.data:
                break
            for row in response.data:
                if row.get("fl_number"):
                    existing.add(row["fl_number"].strip().upper())
            if len(response.data) < batch_size:
                break
            offset += batch_size
    except Exception as e:
        logger.warning(f"Could not fetch existing FL numbers for {vendor}: {e}")
    return existing


def extract_fl_from_filename(filename: str, vendor: str) -> str | None:
    """
    Extract the FL number from a PDF filename.
    Dazpak: typically "FL-CQ-0123 ..."
    Ross: typically "FL-DL-0456 ..."
    Adjust these patterns to match your actual filenames.
    """
    import re
    match = re.search(r"(FL-[A-Z]{2}-\d{3,5})", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def ingest_vendor(vendor: str, folder_id: str, extract_fn, drive_service, supabase) -> dict:
    """
    Full pipeline for one vendor:
    1. List PDFs in Drive folder
    2. Check which FL numbers already exist in Supabase
    3. Download + parse + insert only new ones
    """
    stats = {"total_in_drive": 0, "already_ingested": 0, "newly_ingested": 0, "errors": 0}

    # 1. List all PDFs
    logger.info(f"[{vendor}] Listing PDFs in Drive folder {folder_id}...")
    pdf_files = list_pdfs_in_folder(drive_service, folder_id)
    stats["total_in_drive"] = len(pdf_files)
    logger.info(f"[{vendor}] Found {len(pdf_files)} PDFs in Drive")

    if not pdf_files:
        return stats

    # 2. Get existing FL numbers from Supabase
    existing_fls = get_existing_fl_numbers(supabase, vendor)
    logger.info(f"[{vendor}] {len(existing_fls)} FL numbers already in Supabase")

    # 3. Process each PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        for pdf_file in pdf_files:
            file_name = pdf_file["name"]
            file_id = pdf_file["id"]

            # Layer 1: Filename-level dedup (skip download entirely)
            fl_number = extract_fl_from_filename(file_name, vendor)
            if fl_number and fl_number in existing_fls:
                logger.debug(f"[{vendor}] SKIP (already exists): {fl_number} — {file_name}")
                stats["already_ingested"] += 1
                continue

            # Download PDF
            local_path = os.path.join(tmpdir, file_name)
            try:
                logger.info(f"[{vendor}] Downloading: {file_name}")
                download_pdf(drive_service, file_id, local_path)
            except Exception as e:
                logger.error(f"[{vendor}] Failed to download {file_name}: {e}")
                stats["errors"] += 1
                continue

            # Parse PDF
            try:
                parsed_quotes = extract_fn(local_path)
            except Exception as e:
                logger.error(f"[{vendor}] Failed to parse {file_name}: {e}")
                stats["errors"] += 1
                continue

            if not parsed_quotes:
                logger.warning(f"[{vendor}] No quotes extracted from {file_name}")
                stats["errors"] += 1
                continue

            # Insert each parsed quote
            for quote_data in parsed_quotes:
                # Layer 2: Content-level dedup
                parsed_fl = quote_data.get("fl_number", "").strip().upper()
                if parsed_fl and parsed_fl in existing_fls:
                    logger.debug(f"[{vendor}] SKIP (content-level dedup): {parsed_fl}")
                    stats["already_ingested"] += 1
                    continue

                try:
                    quote_row = {
                        "vendor": vendor,
                        "fl_number": parsed_fl or None,
                        "width": quote_data.get("width"),
                        "height": quote_data.get("height"),
                        "gusset": quote_data.get("gusset", 0),
                        "print_width": quote_data.get("print_width"),
                        "bag_area_sqin": quote_data.get("bag_area_sqin"),
                        "substrate": quote_data.get("substrate"),
                        "finish": quote_data.get("finish"),
                        "fill_style": quote_data.get("fill_style"),
                        "seal_type": quote_data.get("seal_type"),
                        "gusset_type": quote_data.get("gusset_type"),
                        "zipper": quote_data.get("zipper"),
                        "tear_notch": quote_data.get("tear_notch"),
                        "hole_punch": quote_data.get("hole_punch"),
                        "corner_treatment": quote_data.get("corner_treatment"),
                        "embellishment": quote_data.get("embellishment"),
                    }
                    quote_row = {k: v for k, v in quote_row.items() if v is not None}

                    result = supabase.table("quotes").insert(quote_row).execute()
                    quote_id = result.data[0]["id"]

                    # Insert price tiers
                    price_tiers = quote_data.get("price_tiers", [])
                    for i, tier in enumerate(price_tiers):
                        supabase.table("quote_prices").insert({
                            "quote_id": quote_id,
                            "quantity": tier["quantity"],
                            "unit_price": tier["unit_price"],
                            "total_price": tier.get("total_price"),
                            "tier_index": i
                        }).execute()

                    stats["newly_ingested"] += 1
                    if parsed_fl:
                        existing_fls.add(parsed_fl)  # Layer 3: Prevent intra-batch dupes
                    logger.info(f"[{vendor}] INGESTED: {parsed_fl or file_name} ({len(price_tiers)} tiers)")

                except Exception as e:
                    logger.error(f"[{vendor}] Failed to insert {parsed_fl or file_name}: {e}")
                    stats["errors"] += 1

    return stats


def main():
    logger.info("=" * 60)
    logger.info("CALYX AUTO-INGEST — Starting")
    logger.info("=" * 60)

    drive_service = get_google_drive_service()
    supabase = get_client()

    results = {}

    if DAZPAK_FOLDER_ID:
        results["dazpak"] = ingest_vendor(
            vendor="dazpak",
            folder_id=DAZPAK_FOLDER_ID,
            extract_fn=extract_dazpak_pdf,
            drive_service=drive_service,
            supabase=supabase
        )
    else:
        logger.warning("DAZPAK_FOLDER_ID not set, skipping Dazpak")

    if ROSS_FOLDER_ID:
        results["ross"] = ingest_vendor(
            vendor="ross",
            folder_id=ROSS_FOLDER_ID,
            extract_fn=extract_ross_pdf,
            drive_service=drive_service,
            supabase=supabase
        )
    else:
        logger.warning("ROSS_FOLDER_ID not set, skipping Ross")

    # Summary
    logger.info("=" * 60)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 60)
    total_new = 0
    for vendor, stats in results.items():
        logger.info(
            f"  {vendor.upper()}: "
            f"{stats['total_in_drive']} in Drive, "
            f"{stats['already_ingested']} skipped (dupes), "
            f"{stats['newly_ingested']} newly ingested, "
            f"{stats['errors']} errors"
        )
        total_new += stats["newly_ingested"]

    # Set output for GitHub Actions
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"total_new={total_new}\n")

    logger.info(f"Total new quotes ingested: {total_new}")
    return total_new


if __name__ == "__main__":
    new_count = main()
    sys.exit(0)
