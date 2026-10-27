from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_citizen_pdf_upload_api():
    sample_policy = b"""# Sample Tech Policy
We collect name, email, phone to deliver orders.
Data is retained for 30 days and erased afterwards.
Security: TLS 1.3 encryption and access controls.
Grievance: Email nodal.officer@example.com for redressal.
"""
    response = client.post(
        "/api/citizen/analyze-pdf",
        files={"file": ("privacy_notice.txt", sample_policy, "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "dpdp_alignment_score" in data
    assert "citizen_trust_score" in data
    assert "non_compliant_gaps" in data
    assert "all_statutory_comparisons" in data
    assert len(data["all_statutory_comparisons"]) == 11


def test_citizen_compare_similarity_api():
    response = client.post(
        "/api/citizen/compare-similarity",
        json={
            "text": "We provide easy consent withdrawal in settings and erase data upon purpose completion.",
            "filename": "consent_policy.txt",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["dpdp_alignment_score"] > 0
