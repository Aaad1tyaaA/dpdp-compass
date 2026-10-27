#!/usr/bin/env python3
"""Automated end-to-end evaluation script: PDF cosine similarity + DPDP gap analysis.

Demonstrates the citizen pipeline across:
  - Compliant synthetic policy (high alignment)
  - Non-compliant policy (low alignment, flagged gaps)
  - Official DPDP Act 2023 PDF (self-check / statutory ground-truth)
  - Real tech reference policy (Zomato, Blazeit, etc. — benchmark comparison)

Outputs a JSON report with alignment scores, gap counts, and per-obligation cosine
similarities for all 11 statutory DPDP obligations.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure backend root is on sys.path
_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from app.services.pdf_analyzer import analyze_pdf_similarity, DPDP_STATUTORY_OBLIGATIONS


# Try multiple candidate paths for data directories
def _find_data_dir(rel_subpath: str) -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / rel_subpath,
        Path(__file__).resolve().parent.parent.parent / "data" / rel_subpath.replace("data/", ""),
        Path("E:/DPDPRag/project/data") / rel_subpath.replace("data/", ""),
        Path("project/data") / rel_subpath.replace("data/", ""),
        Path("data") / rel_subpath.replace("data/", ""),
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

POLICY_DIR = _find_data_dir("data/company_policies/reference")
LEGAL_DIR = _find_data_dir("data/legal")

BENCHMARKS = [
    ("compliant_policy.txt", b"""# Fully Compliant DPDP Policy
1. Notice: We give itemized notice of personal data collected and purposes.
2. Consent: Free, specific, informed, and unambiguous affirmative consent is required.
3. Withdrawal: You can withdraw consent easily anytime via app toggle in Settings.
4. Security: We apply reasonable security safeguards, AES-256 and TLS 1.3 encryption.
5. Breach: In case of breach, we notify the Data Protection Board and users within 72 hours.
6. Retention: Personal data is erased within 30 days once the purpose is served.
7. Children: We obtain verifiable parental consent and prohibit behavioral tracking of minors.
8. Rights: You have rights to access, correction, erasure, and nomination.
9. Grievance: Contact our designated Grievance Officer at dpo@example.com.
"""),
    ("non_compliant_policy.txt", b"""# Vague Non-Compliant Policy
We collect everything about you.
We retain your data as long as needed at our discretion.
We do not mention anything about security incidents, breaches, children or parental consent.
"""),
]


def _load_real_text(filename: str) -> bytes:
    p = POLICY_DIR / filename
    if p.exists():
        return p.read_bytes()
    # Try .txt with different naming
    for alt in [filename.replace("_", " "), filename.replace(".txt", ".pdf")]:
        alt_p = POLICY_DIR / alt
        if alt_p.exists():
            return alt_p.read_bytes()
    # Try direct file
    p = POLICY_DIR / (filename + ".txt")
    if p.exists():
        return p.read_bytes()
    return b""


async def main():
    results = {}

    # 1. Synthetic compliant
    print("\n[1/5] Synthetic compliant policy ...")
    res = await analyze_pdf_similarity(BENCHMARKS[0][1], BENCHMARKS[0][0])
    results["compliant_synthetic"] = {
        "filename": res["filename"],
        "alignment_score": res["dpdp_alignment_score"],
        "trust_score": res["citizen_trust_score"],
        "summary_counts": res["summary_counts"],
        "gaps": len(res["non_compliant_gaps"]),
        "duration_ms": res.get("duration_ms"),
    }

    # 2. Synthetic non-compliant
    print("[2/5] Synthetic non-compliant policy ...")
    res = await analyze_pdf_similarity(BENCHMARKS[1][1], BENCHMARKS[1][0])
    results["non_compliant_synthetic"] = {
        "filename": res["filename"],
        "alignment_score": res["dpdp_alignment_score"],
        "trust_score": res["citizen_trust_score"],
        "summary_counts": res["summary_counts"],
        "gaps": len(res["non_compliant_gaps"]),
        "duration_ms": res.get("duration_ms"),
    }

    # 3. Real DPDP Act PDF (self-check against its own obligations)
    print("[3/5] Official DPDP Act 2023 PDF (21 pages) ...")
    dpdp_pdf = LEGAL_DIR / "DPDP_Act_2023.pdf"
    if dpdp_pdf.exists():
        res = await analyze_pdf_similarity(dpdp_pdf.read_bytes(), "DPDP_Act_2023.pdf")
    else:
        res = {"status": "SKIPPED", "reason": "DPDP_Act_2023.pdf not found"}
    results["dpdp_act_self_check"] = {
        "filename": res.get("filename"),
        "alignment_score": res.get("dpdp_alignment_score"),
        "trust_score": res.get("citizen_trust_score"),
        "pages": res.get("total_pages"),
        "clauses": res.get("total_clauses_analyzed"),
        "summary_counts": res.get("summary_counts"),
        "duration_ms": res.get("duration_ms"),
    }

    # 4. Zomato reference policy (real tech benchmark)
    print("[4/5] Real tech reference — Zomato ...")
    txt = _load_real_text("Zomato_Privacy_Policy.txt")
    if txt:
        res = await analyze_pdf_similarity(txt, "Zomato_Privacy_Policy.txt")
    else:
        res = {"status": "SKIPPED", "reason": "Zomato file missing"}
    results["zomato_reference"] = {
        "filename": res.get("filename"),
        "alignment_score": res.get("dpdp_alignment_score"),
        "trust_score": res.get("citizen_trust_score"),
        "summary_counts": res.get("summary_counts"),
        "gaps": len(res.get("non_compliant_gaps", [])),
    }

    # 5. Per-obligation comparison matrix (from compliant synthetic for reference)
    print("[5/5] Building obligation-level matrix ...")
    res = await analyze_pdf_similarity(BENCHMARKS[0][1], BENCHMARKS[0][0])
    obligation_matrix = []
    for item in res.get("all_statutory_comparisons", []):
        obligation_matrix.append({
            "obligation_id": item["obligation_id"],
            "section": item["dpdp_section"],
            "title": item["dpdp_title"],
            "status": item["status"],
            "similarity": item["cosine_similarity"],
            "criticality": item["criticality"],
        })
    results["obligation_matrix_sample"] = obligation_matrix

    # Write report
    report_path = Path(__file__).resolve().parent / "e2e_evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "evaluated_at": datetime.utcnow().isoformat() + "Z",
            "engine": "DPDP Act 2023 Cosine Similarity + Gap Analysis",
            "pipeline": "extract -> clause_chunk -> embed (384d) -> cosine -> classify",
            "results": results,
            "summary": {
                "tests_run": 5,
                "compliant_alignment": results["compliant_synthetic"]["alignment_score"],
                "non_compliant_alignment": results["non_compliant_synthetic"]["alignment_score"],
                "dpdp_act_self_check": results.get("dpdp_act_self_check", {}).get("alignment_score"),
                "zomato_reference": results.get("zomato_reference", {}).get("alignment_score"),
            }
        }, f, indent=2, default=str)

    print(f"\n=== EVALUATION COMPLETE ===")
    print(f"Report: {report_path}")
    for k, v in results.items():
        if isinstance(v, dict) and "alignment_score" in v:
            print(f"  {k}: alignment={v.get('alignment_score')}, trust={v.get('trust_score')}, gaps={v.get('gaps')}")
    return results


if __name__ == "__main__":
    asyncio.run(main())
