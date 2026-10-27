"""Master-spec compliance — fast, no model download, no API key needed."""
from pathlib import Path

def test_builder_discovers_directory_windows_safe(tmp_path):
    from app.knowledge_base.builder import discover_files
    (tmp_path / "a.pdf").write_bytes(b"%PDF fake")
    (tmp_path / "b.txt").write_text("Section 8 test")
    (tmp_path / "ignore.exe").write_bytes(b"x")
    files = discover_files([str(tmp_path)])
    names = {f.name for f in files}
    assert "a.pdf" in names and "b.txt" in names and "ignore.exe" not in names

def test_openrouter_key_field_exists():
    from app.config import Settings
    assert "openrouter_api_key" in Settings.model_fields
    assert "openrouter_base_url" in Settings.model_fields

def test_llm_gateway_has_fallbacks_and_guard():
    from app.services import llm as llm_mod
    assert hasattr(llm_mod, "OpenAICompatibleProvider")
    assert "INSUFFICIENT_EVIDENCE" in llm_mod.EVIDENCE_GUARD
    assert "prompt injection" in llm_mod.EVIDENCE_GUARD.lower()

def test_model_discovery_offline_ranking():
    from app.services.model_discovery import score_candidate, FALLBACK_CANDIDATES
    ranked = sorted(FALLBACK_CANDIDATES, key=lambda m: score_candidate(m)[0], reverse=True)
    assert ranked[0]["free"] is True
    assert ranked[0].get("context", 0) >= 32000

def test_trust_methodology_doc_exists():
    assert Path("..\\docs\\trust_methodology.md").exists() or (Path(__file__).resolve().parents[2] / "docs" / "trust_methodology.md").exists()

def test_gitignore_protects_env():
    p = Path(__file__).resolve().parents[2] / ".gitignore"
    assert p.exists()
    assert ".env" in p.read_text()

def test_hybrid_retrieval_exposes_diagnostics():
    from app.retrieval import hybrid_retriever
    assert hasattr(hybrid_retriever, "last_retrieval_diag")

def test_orchestrator_returns_insufficient_status_field():
    import inspect
    from app.agents import orchestrator
    src = inspect.getsource(orchestrator.orchestrate)
    assert "INSUFFICIENT_EVIDENCE" in src
    assert "model_used" in src
