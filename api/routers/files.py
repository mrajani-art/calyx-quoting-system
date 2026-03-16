"""
File upload router.

POST /api/v1/files/upload - Upload customer artwork files to Supabase Storage.
"""
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.services.supabase_client import upload_file_to_storage, insert_file_record, get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["files"])

MAX_FILES = 10
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/pdf",
    "application/postscript",
    "application/illustrator",
    "image/vnd.adobe.photoshop",
    "application/octet-stream",
}


@router.post("/files/upload")
async def upload_files(
    lead_id: str = Form(...),
    quote_id: str | None = Form(default=None),
    files: list[UploadFile] = File(...),
):
    """
    Upload one or more customer artwork files.

    Files are stored in Supabase Storage under the customer-artwork bucket
    and tracked in the customer_files table.
    """
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum is {MAX_FILES}.",
        )

    # Validate lead exists
    sb = get_supabase()
    lead_check = sb.table("customer_leads").select("id").eq("id", lead_id).execute()
    if not lead_check.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    uploaded = []

    for f in files:
        # Validate content type
        content_type = f.content_type or "application/octet-stream"
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{content_type}' is not allowed for file '{f.filename}'.",
            )

        # Read and validate size
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' exceeds the 25 MB size limit.",
            )

        file_name = f.filename or "unnamed"

        # Upload to Supabase Storage
        try:
            storage_path, public_url = upload_file_to_storage(
                lead_id=lead_id,
                file_name=file_name,
                file_content=content,
                content_type=content_type,
            )
        except Exception as e:
            logger.error(f"Storage upload failed for '{file_name}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file '{file_name}'.",
            )

        # Insert tracking record
        try:
            record = insert_file_record({
                "lead_id": lead_id,
                "quote_id": quote_id,
                "file_name": file_name,
                "file_type": content_type,
                "file_size": len(content),
                "storage_path": storage_path,
                "public_url": public_url,
            })
            uploaded.append({
                "id": record.get("id"),
                "file_name": file_name,
                "public_url": public_url,
            })
        except Exception as e:
            # Attempt to clean up the orphaned storage file
            try:
                get_supabase().storage.from_("customer-artwork").remove([storage_path])
            except Exception:
                logger.warning(f"Failed to clean up orphaned file: {storage_path}")
            logger.error(f"Failed to insert file record for '{file_name}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file record for '{file_name}'.",
            )

    logger.info(f"Uploaded {len(uploaded)} file(s) for lead {lead_id}")
    return {"uploaded": uploaded}
