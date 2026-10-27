from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_env = Path(__file__).resolve().parent.parent / ".env"
_project_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
_cwd_env = Path.cwd() / ".env"

_env_files = [str(p) for p in [_backend_env, _project_env, _cwd_env] if p.exists()]
if not _env_files:
    _env_files = [str(_backend_env)]


class Settings(BaseSettings):
    app_name: str = "DPDP RAG System"
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_fallback_api_keys: SecretStr | None = None  # comma-separated backup keys, used when the main key is rate-limited or rejected
    llm_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    llm_fallback_models: str = "deepseek/deepseek-r1:free,qwen/qwen-2.5-72b-instruct:free,google/gemma-3-27b-it:free,mistralai/mistral-small-3.1-24b-instruct:free,openrouter/free"
    mock_llm: bool = True
    llm_provider: str = "openai"
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096
    llm_max_retries: int = 3
    llm_timeout: float = 60.0
    llm_reasoning_effort: str = "low"  # gpt-oss models: low|medium|high ("" to omit)
    llm_rate_limit_cooldown_seconds: int = 60

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_legal_collection: str = "dpdp_legal_kb"
    qdrant_company_collection: str = "company_policy_kb"
    qdrant_collection: str = "dpdp_chunks"
    chroma_url: str = "http://localhost:8001"
    chroma_collection: str = "dpdp_chunks"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    vector_store: str = "qdrant"

    database_url: str = "postgresql://dpdp:dpdp@localhost:5432/dpdp"
    postgres_url: str = "postgresql://dpdp:dpdp@localhost:5432/dpdp"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("password")

    dpdp_documents_path: str = "./data/dpdp"
    reference_policies_path: str = "./data/company_policies/reference"
    upload_storage_path: str = "./storage/original_documents"
    enable_ocr: bool = False
    enable_knowledge_graph: bool = True
    ingestion_background_mode: bool = True

    top_k: int = 8
    sparse_top_k: int = 8
    rerank_top_n: int = 5
    hybrid_alpha: float = 0.7
    rrf_k: int = 60
    max_feedback_iterations: int = 3
    max_corrective_retries: int = 2
    evidence_threshold: float = 0.35
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings(_env_file=_env_files)
if not settings.llm_api_key:
    settings.llm_api_key = settings.openrouter_api_key or settings.openai_api_key
if not settings.llm_base_url:
    settings.llm_base_url = settings.openrouter_base_url
_settings_env_files = _env_files


def reveal(secret: SecretStr | None) -> str | None:
    """Plain value of a secret setting. Secrets are SecretStr so they print as '**********' in logs/errors."""
    return secret.get_secret_value() if secret else None


def effective_llm_key() -> str | None:
    return reveal(settings.openrouter_api_key or settings.llm_api_key or settings.openai_api_key)


def port_open(url: str, timeout: float = 0.3) -> bool:
    """Fast reachability probe for a service URL (http://, bolt://, ...). On Windows a refused local
    connection takes ~2s per attempt (plus an IPv6 try for "localhost"); probing first makes a
    service that isn't running cost ~0.3s at startup instead of ~4s."""
    import socket
    from urllib.parse import urlparse
    u = urlparse(url)
    host = "127.0.0.1" if u.hostname in (None, "localhost") else u.hostname
    port = u.port or {"http": 80, "https": 443, "bolt": 7687, "neo4j": 7687}.get(u.scheme, 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
