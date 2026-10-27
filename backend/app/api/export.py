import re
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportBody(BaseModel):
    markdown: str = Field(..., max_length=500_000)
    title: str = Field("DPDP Compass document", max_length=200)
    subtitle: str = Field("", max_length=300)
    format: Literal["md", "pdf", "docx"]


@router.post("")
async def export_document(body: ExportBody):
    """Render the same Markdown as a .md, .pdf or .docx download."""
    if not body.markdown.strip():
        raise HTTPException(status_code=400, detail="Nothing to export")
    from app.services.exporter import export
    try:
        data, media, ext = export(body.markdown, body.title, body.format, body.subtitle)
    except Exception as e:  # rendering bugs must surface as a clear error, not a corrupt file
        raise HTTPException(status_code=500, detail=f"Could not create the {body.format.upper()} file: {e}")
    stem = re.sub(r"[^A-Za-z0-9]+", "-", body.title).strip("-").lower()[:80] or "document"
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{stem}.{ext}"'})
