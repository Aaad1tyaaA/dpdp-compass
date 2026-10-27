from pathlib import Path
from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".html", ".htm"}


async def read_upload(file: UploadFile) -> bytes:
    """Validate extension + size, return bytes. Reads at most MAX+1 bytes so huge files can't exhaust memory."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type '{ext or 'none'}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return content
