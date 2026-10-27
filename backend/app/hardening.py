"""Production hardening applied to the FastAPI app: request ids, structured access logs, security
headers, a request-size limit, safe error responses and a readiness probe.

    ENV=production            hides /docs and internal details in /health
    MAX_BODY_BYTES=12000000   largest accepted request body (uploads included)
    TRUSTED_HOSTS=a.com,b.com Host header allowlist (unset = any)
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

PRODUCTION = os.getenv("ENV", "development").lower() == "production"
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", str(12 * 1024 * 1024)))
access = logging.getLogger("app.access")
log = logging.getLogger("app.errors")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",  # the API serves JSON only
}


def docs_urls() -> dict:
    """Interactive docs are useful in development and an unnecessary surface in production."""
    return {"docs_url": None, "redoc_url": None, "openapi_url": None} if PRODUCTION else {}


def harden(app: FastAPI) -> None:
    hosts = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "").split(",") if h.strip()]
    if hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        start = time.perf_counter()
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            response = JSONResponse({"detail": f"request body larger than {MAX_BODY_BYTES} bytes", "request_id": rid}, status_code=413)
        else:
            try:
                response = await call_next(request)
            except Exception:  # never leak a stack trace to the client; the log line carries the request id
                log.exception("unhandled error request_id=%s path=%s", rid, request.url.path)
                response = JSONResponse({"detail": "internal error", "request_id": rid}, status_code=500)
        response.headers["X-Request-ID"] = rid
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path not in ("/health", "/ready"):
            # Paths only: query strings and bodies can hold personal data and are never logged.
            access.info(json.dumps({"request_id": rid, "method": request.method, "path": request.url.path, "status": response.status_code,
                                    "ms": round((time.perf_counter() - start) * 1000), "ip": request.client.host if request.client else None}))
        return response

    @app.get("/ready", include_in_schema=False)
    async def ready():
        """Readiness: the statute knowledge base and its index are built and searchable."""
        from app.compass.audit import get_engine
        if get_engine.cache_info().currsize == 0:
            return JSONResponse({"status": "starting"}, status_code=503)
        e = get_engine(rules=True)
        return {"status": "ready", "chunks": len(e.chunks), "obligations": len(e.kb.obligations)}


def warm_engine() -> None:
    """Build the knowledge base and load the embedding and re-ranking models before the first request."""
    try:
        from app.compass.audit import get_engine
        get_engine(rules=True).index.search("warm up", k=1)
        logging.getLogger("app").info("Compass engine ready")
    except Exception:
        log.exception("engine warm-up failed")
