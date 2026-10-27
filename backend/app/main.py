import os
import asyncio
import logging
from contextlib import asynccontextmanager
import secrets
import time
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.policies import router as policies_router
from app.api.compliance import router as compliance_router
from app.api.citizen import router as citizen_router
from app.api.documents import router as documents_router
from app.api.evaluation import router as evaluation_router
from app.api.export import router as export_router
from app.hardening import PRODUCTION, docs_urls, harden, warm_engine
from app import auth
from app.api.compliance import current_uid

def _use_cached_models_offline() -> None:
    """If the embedding + reranker models are already downloaded, skip Hugging Face's online update
    checks (measured: model loads 9.0s -> 1.0s). A fresh machine still downloads normally.
    Must run before anything imports huggingface_hub, which reads HF_HUB_OFFLINE at import."""
    if "HF_HUB_OFFLINE" in os.environ:
        return
    try:
        from huggingface_hub import try_to_load_from_cache
        from app.config import settings
        if all(isinstance(try_to_load_from_cache(m, "config.json"), str) for m in (settings.embedding_model, settings.reranker_model)):
            os.environ["HF_HUB_OFFLINE"] = "1"
            import huggingface_hub.constants as c
            c.HF_HUB_OFFLINE = True
    except Exception:
        pass


_use_cached_models_offline()

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(logging.INFO)  # our own INFO logs (timings, fallbacks); libraries stay at WARNING
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-seed the Gazette DPDP Act 2023 & Tech Reference Policies on startup if store is empty
    try:
        from app.knowledge_base.auto_indexer import initialize_default_knowledge_base
        # Indexing is CPU/blocking-IO heavy (model load, PDF parse); keep it off the event loop
        # so the API answers requests while the KB warms up.
        async def _startup():
            # One after the other: both load models, and concurrent model initialisation is not thread-safe.
            try:
                await asyncio.to_thread(asyncio.run, initialize_default_knowledge_base())
            finally:
                await asyncio.to_thread(warm_engine)  # /ready turns 200 once the engine is built
        asyncio.create_task(_startup())
        logger.info("Knowledge base start-up task launched")
    except Exception as e:
        logger.warning("Knowledge base startup initialization error: %s", e)
    yield


app = FastAPI(
    title="DPDP RAG System",
    version="1.0.0",
    description="Multilingual Multi-Agent RAG for DPDP Act Compliance & Citizen Rights",
    lifespan=lifespan,
    **docs_urls(),
)
harden(app)

_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:5173,"
                                             "http://127.0.0.1:3000,http://127.0.0.1:3001").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    # Wildcard origin + credentials is invalid per the Fetch spec; use an explicit allowlist.
    allow_origins=_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_API_KEY = os.getenv("API_KEY", "")
_RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
_hits: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def auth_and_rate_limit(request: Request, call_next):
    """Guard write/LLM endpoints: optional X-API-Key (set API_KEY to enable) + per-IP rate limit.
    ponytail: in-process sliding window; move to Redis/slowapi when running >1 worker."""
    path = request.url.path
    user = auth.user_for(request) if path.startswith("/api/") else None
    request.state.user = user
    current_uid.set(user["id"] if user else None)
    service = bool(_API_KEY) and secrets.compare_digest(request.headers.get("x-api-key", ""), _API_KEY)
    if path.startswith("/api/") and request.method != "OPTIONS":
        if user and request.method not in ("GET", "HEAD"):
            # Cross-site request forgery: a browser sends the session cookie with requests made by other
            # sites, so a state-changing request must come from one of our own origins.
            origin = request.headers.get("origin")
            if origin and origin not in _ORIGINS and origin.split("://")[-1] != request.headers.get("host"):
                return JSONResponse({"detail": "cross-site request refused"}, status_code=403)
        open_path = path.startswith("/api/auth/") or path == "/api/version"
        if auth.auth_required() and not open_path and not user and not service:
            return JSONResponse({"detail": "sign in to continue"}, status_code=401)
    if request.method == "POST" and path.startswith("/api/"):
        if _API_KEY and not user and not service:
            return JSONResponse({"detail": "invalid or missing X-API-Key"}, status_code=401)
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = [t for t in _hits[ip] if now - t < 60]
        if len(window) >= _RATE_LIMIT_PER_MIN:
            return JSONResponse({"detail": "rate limit exceeded, retry in a minute"}, status_code=429, headers={"Retry-After": "60"})
        window.append(now)
        _hits[ip] = window
    return await call_next(request)


app.include_router(documents_router)
app.include_router(policies_router)
app.include_router(compliance_router)
app.include_router(citizen_router)
app.include_router(evaluation_router)
app.include_router(export_router)
app.include_router(auth.router)
from app.api.compass import router as compass_router  # noqa: E402
app.include_router(compass_router)


@app.get("/health")
async def health():
    from app.config import settings, _settings_env_files
    from app.knowledge_base import vector_store
    from app.config import effective_llm_key
    key = effective_llm_key()
    legal_docs = vector_store.count(settings.qdrant_legal_collection)
    company_docs = vector_store.count(settings.qdrant_company_collection)
    if PRODUCTION:  # liveness only: no configuration details on a public endpoint
        return {"status": "ok", "llm_configured": bool(key) and not settings.mock_llm, "legal_kb_records": legal_docs}
    return {
        "status": "ok",
        "mock_llm": settings.mock_llm,
        "llm_model": settings.llm_model,
        "llm_base_url": settings.llm_base_url,
        "has_key": bool(key),
        "key_prefix": key[:7] + "..." if key and len(key) > 7 else None,
        "env_files_tried": _settings_env_files,
        "legal_kb_records": legal_docs,
        "company_kb_records": company_docs,
    }


@app.get("/api/version")
async def version():
    return {
        "version": "1.0.0",
        "evidence_first": True,
        "multilingual": True,
        "dpdp_act_gazette_embedded": True,
        "reference_tech_policies_embedded": True,
    }
