import pytest
from app.services.pdf_analyzer import analyze_pdf_similarity, cosine_similarity, DPDP_STATUTORY_OBLIGATIONS


def test_cosine_similarity_orthogonal_and_identical():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_pdf_analyzer_on_compliant_policy():
    compliant_policy = b"""# Fully Compliant DPDP Policy
1. Notice: We give itemized notice of personal data collected and purposes.
2. Consent: Free, specific, informed, and unambiguous affirmative consent is required.
3. Withdrawal: You can withdraw consent easily anytime via app toggle in Settings.
4. Security: We apply reasonable security safeguards, AES-256 and TLS 1.3 encryption.
5. Breach: In case of breach, we notify the Data Protection Board and users within 72 hours.
6. Retention: Personal data is erased within 30 days once the purpose is served.
7. Children: We obtain verifiable parental consent and prohibit behavioral tracking of minors.
8. Rights: You have rights to access, correction, erasure, and nomination.
9. Grievance: Contact our designated Grievance Officer at dpo@example.com.
"""
    result = await analyze_pdf_similarity(compliant_policy, "compliant_policy.txt")
    assert result["status"] == "SUCCESS"
    assert result["dpdp_alignment_score"] >= 65
    assert result["citizen_trust_score"] >= 60
    assert result["summary_counts"]["total_statutory_obligations"] == len(DPDP_STATUTORY_OBLIGATIONS)
    assert len(result["compliant_clauses"]) >= 5


@pytest.mark.asyncio
async def test_pdf_analyzer_detects_non_compliant_gaps():
    non_compliant_policy = b"""# Vague Non-Compliant Policy
We collect everything about you.
We retain your data as long as needed at our discretion.
We do not mention anything about security incidents, breaches, children or parental consent.
"""
    result = await analyze_pdf_similarity(non_compliant_policy, "bad_policy.txt")
    assert result["status"] == "SUCCESS"
    assert result["dpdp_alignment_score"] < 50
    gaps = result["non_compliant_gaps"]
    assert len(gaps) >= 3

    # Verify breach notification gap is flagged
    breach_gap = next((g for g in gaps if g["obligation_id"] == "dpdp_breach_notice"), None)
    assert breach_gap is not None
    assert breach_gap["status"] in ("MISSING", "PARTIAL")

    # Verify retention gap is flagged
    retention_gap = next((g for g in gaps if g["obligation_id"] == "dpdp_retention_erasure"), None)
    assert retention_gap is not None
    assert retention_gap["status"] in ("PARTIAL", "MISSING")
