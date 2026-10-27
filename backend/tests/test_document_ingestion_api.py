import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.knowledge_base import vector_store
from app.main import app


client = TestClient(app)


def test_document_upload_defaults_to_policy_kb():
    vector_store.reset_for_tests()
    response = client.post(
        "/api/documents/upload",
        files={"file": ("privacy_policy.txt", b"We collect email for support and retain records for 30 days.", "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_type"] == "POLICY"
    assert payload["authority_level"] == "REFERENCE"
    assert vector_store.count(settings.qdrant_company_collection) >= 1
    assert vector_store.count(settings.qdrant_legal_collection) == 0


def test_document_upload_explicit_legal_goes_to_legal_kb():
    vector_store.reset_for_tests()
    response = client.post(
        "/api/documents/upload?source_type=LEGAL&authority_level=PRIMARY",
        files={"file": ("dpdp.txt", b"Section 8 Data Fiduciary shall protect personal data.", "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_type"] == "LEGAL"
    assert payload["authority_level"] == "PRIMARY"
    assert vector_store.count(settings.qdrant_legal_collection) >= 1
    assert vector_store.count(settings.qdrant_company_collection) == 0


def test_ingest_url_defaults_to_policy_kb(monkeypatch):
    vector_store.reset_for_tests()
    # Hermetic: the SSRF guard resolves the host; don't depend on real DNS (made this test flaky).
    import socket
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", 0))])

    async def fake_get(self, url, headers=None):
        return httpx.Response(
            200,
            content=b"<html><body>Privacy policy: we collect name and provide deletion rights.</body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    response = client.post("/api/documents/ingest-url", json={"url": "https://example.com/privacy"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_type"] == "POLICY"
    assert vector_store.count(settings.qdrant_company_collection) >= 1
    assert vector_store.count(settings.qdrant_legal_collection) == 0
