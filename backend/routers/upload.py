"""
Image upload router.

Endpoint:
  POST /upload/image — accepts jpg/png/webp, saves to uploads/images/,
                        returns {file_id, base64}
"""

import os
import uuid
import base64

from fastapi import APIRouter, UploadFile, File, HTTPException


router = APIRouter(prefix="/upload", tags=["upload"])


IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "uploads",
    "images",
)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image file for chat attachments.

    Accepts: jpg, png, webp (max 10MB)
    Returns: {file_id, base64, filename, content_type}
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. "
                   f"Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    content = await file.read()

    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large ({len(content)} bytes). Max: {MAX_IMAGE_SIZE} bytes.",
        )

    # Generate unique filename
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{ext}"

    # Save to disk
    os.makedirs(IMAGES_DIR, exist_ok=True)
    filepath = os.path.join(IMAGES_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    # Encode to base64 for frontend preview and chat embedding
    b64 = base64.b64encode(content).decode("utf-8")

    return {
        "file_id": file_id,
        "base64": b64,
        "filename": file.filename,
        "content_type": file.content_type,
    }
