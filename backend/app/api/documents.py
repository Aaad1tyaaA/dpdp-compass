from fastapi import APIRouter, UploadFile, File, HTTPException
from datetime import datetime
import uuid
import logging
import hashlib
import re
from urllib.parse import urlparse, urljoin
import ipaddress
import socket
from pydantic import BaseModel
from app.api.uploads import read_upload, MAX_UPLOAD_BYTES

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)

_in_memory_docs: dict[str, dict] = {}


def _resolve_source(source_type: str | None, authority_level: str | None, filename: str, company_id: str | None) -> tuple[str, str, str | None]:
    if source_type:
        resolved_source = source_type.upper()
    else:
        name = filename.lower()
        legal_name = bool(re.search(r"\bdpdp\b|digital[\W_]+personal[\W_]+data[\W_]+protection", name))
        resolved_source = "LEGAL" if legal_name else "POLICY"
    if resolved_source not in {"LEGAL", "POLICY"}:
        raise HTTPException(status_code=400, detail="source_type must be LEGAL or POLICY")
    resolved_authority = (authority_level or ("PRIMARY" if resolved_source == "LEGAL" else "REFERENCE")).upper()
    if resolved_source == "POLICY" and not company_id:
        company_id = "uploaded_policy"
    return resolved_source, resolved_authority, company_id


def _assert_public_host(url: str) -> None:
    """SSRF guard: every resolved address must be public (blocks 127.0.0.1, 10/8, 169.254.169.254, ...).
    ponytail: resolve-then-fetch leaves a DNS-rebinding window; pin the resolved IP if this is ever internet-facing."""
    host = urlparse(url).hostname or ""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail=f"Could not resolve host {host!r}")
    for info in infos:
        if not ipaddress.ip_address(info[4][0].split("%")[0]).is_global:
            raise HTTPException(status_code=400, detail="URL resolves to a private or reserved address")


class IngestUrlBody(BaseModel):
    url: str
    company_id: str | None = None
    source_type: str | None = None
    authority_level: str | None = None
    filename: str | None = None
    document_id: str | None = None
    source_document: str | None = None


def _filename_from_url(url: str, content_type: str | None) -> str:
    path_name = urlparse(url).path.rsplit("/", 1)[-1]
    if path_name and "." in path_name:
        return path_name[:120]
    if content_type and "pdf" in content_type.lower():
        return "downloaded.pdf"
    return "downloaded.html"


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    company_id: str | None = None,
    source_type: str | None = None,
    authority_level: str | None = None,
):
    content = await read_upload(file)
    filename = file.filename or "unknown.pdf"
    document_id = f"doc_{uuid.uuid4().hex[:8]}"
    doc_hash = hashlib.sha256(content).hexdigest()
    for existing in _in_memory_docs.values():
        if existing.get("document_hash") == doc_hash:
            return {
                "document_id": existing["document_id"],
                "status": "DUPLICATE",
                "message": "Document already processed",
            }
    from app.ingestion.ingestion_service import ingest_document
    resolved_source, resolved_authority, company_id = _resolve_source(source_type, authority_level, filename, company_id)
    try:
        result = await ingest_document(
            content=content, filename=filename, document_id=document_id,
            company_id=company_id,
            source_type=resolved_source,
            authority_level=resolved_authority,
        )
        _in_memory_docs[document_id] = {**result, "uploaded_at": datetime.utcnow().isoformat()}
        return result
    except Exception as e:
        logger.error("ingestion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest-url")
async def ingest_url(body: IngestUrlBody):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="url must be an http(s) URL")

    source_type, authority_level, company_id = _resolve_source(
        body.source_type, body.authority_level, url, body.company_id
    )
    try:
        import httpx
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            for _ in range(5):  # follow redirects manually so every hop passes the SSRF check
                _assert_public_host(url)
                response = await client.get(url, headers={"User-Agent": "DPDP-RAG/1.0"})
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                # ponytail: body is buffered before the size check; stream it if hostile URLs become a concern
                content = response.content
                if len(content) > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Remote document exceeds 10 MB limit")
                break
            else:
                raise HTTPException(status_code=400, detail="Too many redirects")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("url fetch failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {str(e)}")

    filename = body.filename or _filename_from_url(url, response.headers.get("content-type"))
    document_id = body.document_id or f"url_{hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]}"
    doc_hash = hashlib.sha256(content).hexdigest()
    for existing in _in_memory_docs.values():
        if existing.get("document_hash") == doc_hash:
            return {
                "document_id": existing["document_id"],
                "status": "DUPLICATE",
                "message": "Document already processed",
            }

    from app.ingestion.ingestion_service import ingest_document
    try:
        result = await ingest_document(
            content=content,
            filename=filename,
            document_id=document_id,
            company_id=company_id,
            source_type=source_type,
            authority_level=authority_level,
            source_document=body.source_document or url,
        )
        _in_memory_docs[document_id] = {**result, "url": url, "uploaded_at": datetime.utcnow().isoformat()}
        return result
    except Exception as e:
        logger.error("url ingestion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/{document_id}/status")
async def get_status(document_id: str):
    doc = _in_memory_docs.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "document_id": doc.get("document_id"),
        "document_name": doc.get("document_name"),
        "status": doc.get("status"),
        "chunks": doc.get("chunks"),
        "triplets": doc.get("triplets"),
        "vector_count": doc.get("vector_count"),
        "source_type": doc.get("source_type"),
        "duration_ms": doc.get("duration_ms"),
    }


@router.get("")
async def list_documents():
    return list(_in_memory_docs.values())


@router.post("/{document_id}/reprocess")
async def reprocess(document_id: str):
    doc = _in_memory_docs.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    from pathlib import Path
    from app.config import settings
    orig = Path(settings.upload_storage_path) / document_id
    pdf_files = list(orig.glob("*.pdf")) + list(orig.glob("*.txt")) + list(orig.glob("*.docx"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="Original file not found")
    content = pdf_files[0].read_bytes()
    from app.ingestion.ingestion_service import ingest_document
    result = await ingest_document(
        content=content, filename=doc.get("document_name", pdf_files[0].name),
        document_id=document_id, company_id=doc.get("company_id"),
        source_type=doc.get("source_type", "LEGAL"),
        authority_level=doc.get("authority_level", "PRIMARY"),
    )
    _in_memory_docs[document_id] = {**result, "uploaded_at": doc.get("uploaded_at"), "reprocessed_at": datetime.utcnow().isoformat()}
    return result
