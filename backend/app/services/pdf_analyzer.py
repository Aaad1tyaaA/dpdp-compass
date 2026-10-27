"""Citizen PDF Privacy Policy Similarity & DPDP Gap Analysis Engine.

Extracts text from uploaded PDF privacy policies, computes dense cosine similarity
against DPDP Act 2023 statutory obligations, classifies compliance status (SATISFIED,
PARTIAL, MISSING), and generates plain-language explanations of non-compliant gaps.
"""
import logging
import math
import time
import re
from typing import Any
from app.ingestion.parsers import parse_document
from app.ingestion.clause_chunker import clause_aware_chunk
from app.knowledge_base.embedding_generator import generate_embeddings
from app.knowledge_base import vector_store
from app.config import settings

logger = logging.getLogger(__name__)

# Canonical DPDP Act 2023 Statutory Obligations
DPDP_STATUTORY_OBLIGATIONS = [
    {
        "id": "dpdp_notice",
        "section": "Section 5 & 6",
        "title": "Clear Pre-Consent Notice",
        "description": "Data fiduciary must provide clear notice with itemized categories of personal data collected, specific purpose, manner of exercising rights, and grievance officer details before or at time of consent.",
        "keywords": ["notice", "purpose", "itemised", "description", "manner", "grievance"],
        "criticality": "HIGH",
    },
    {
        "id": "dpdp_consent",
        "section": "Section 6(1) & 6(2)",
        "title": "Free, Specific, Informed & Unconditional Consent",
        "description": "Consent must be free, specific, informed, unconditional, and unambiguous with clear affirmative action. Bundled consent or pre-checked consent is prohibited.",
        "keywords": ["consent", "free", "specific", "informed", "unconditional", "unambiguous", "affirmative"],
        "criticality": "HIGH",
    },
    {
        "id": "dpdp_withdrawal",
        "section": "Section 6(4)",
        "title": "Ease of Consent Withdrawal",
        "description": "Data principal has the right to withdraw consent anytime with ease comparable to giving consent (e.g., simple one-click or in-app toggle without dark patterns).",
        "keywords": ["withdraw", "withdrawal", "revoke", "opt-out", "ease", "comparable"],
        "criticality": "HIGH",
    },
    {
        "id": "dpdp_security",
        "section": "Section 8(5)",
        "title": "Reasonable Security Safeguards",
        "description": "Data fiduciary must implement reasonable technical and organizational security safeguards (encryption, access controls, audits) to prevent personal data breach.",
        "keywords": ["security", "safeguards", "encryption", "technical", "organizational", "measures", "protect"],
        "criticality": "HIGH",
    },
    {
        "id": "dpdp_breach_notice",
        "section": "Section 8(6) & Rule 10",
        "title": "Mandatory 72-Hour Personal Data Breach Notification",
        "description": "In the event of a personal data breach, data fiduciary must notify the Data Protection Board of India and each affected Data Principal in prescribed form and timeline.",
        "keywords": ["breach", "incident", "notification", "notify", "board", "72 hours", "intimation"],
        "criticality": "HIGH",
    },
    {
        "id": "dpdp_retention_erasure",
        "section": "Section 8(7)",
        "title": "Retention Limitation & Purpose Erasure",
        "description": "Data fiduciary must erase personal data as soon as the specified purpose is fulfilled or consent is withdrawn. Vague indefinite retention is strictly prohibited.",
        "keywords": ["retention", "erase", "erasure", "delete", "deletion", "purge", "storage limit", "as long as needed"],
        "criticality": "HIGH",
    },
    {
        "id": "dpdp_children",
        "section": "Section 9(1) & 9(3)",
        "title": "Children's Data Protection & Parental Consent",
        "description": "Data fiduciary must obtain verifiable parental consent before processing child data (<18 years) and is prohibited from behavioral tracking, profiling, or targeted ads directed at children.",
        "keywords": ["child", "children", "minor", "parental consent", "guardian", "behavioral tracking", "targeted advertising"],
        "criticality": "HIGH",
    },
    {
        "id": "dpdp_access_info",
        "section": "Section 11",
        "title": "Right to Access Summary & Third-Party Sharing Details",
        "description": "Data principal has the right to obtain a summary of personal data being processed, identities of all fiduciaries/processors shared with, and other relevant information.",
        "keywords": ["access", "summary", "identities", "third parties", "shared with", "categories"],
        "criticality": "MEDIUM",
    },
    {
        "id": "dpdp_correction",
        "section": "Section 12",
        "title": "Right to Correction, Completion & Updating",
        "description": "Data principal has the right to correction of inaccurate personal data, completion of incomplete data, and updating of outdated personal data.",
        "keywords": ["correct", "correction", "update", "rectify", "inaccurate", "incomplete"],
        "criticality": "MEDIUM",
    },
    {
        "id": "dpdp_grievance",
        "section": "Section 13 & 8",
        "title": "Accessible Grievance Redressal & DPO",
        "description": "Data fiduciary must publish name, contact address, and email of a designated Grievance Officer / DPO to redress complaints within reasonable response timelines.",
        "keywords": ["grievance", "redressal", "officer", "dpo", "contact", "complaint", "nodal"],
        "criticality": "HIGH",
    },
    {
        "id": "dpdp_nomination",
        "section": "Section 14",
        "title": "Right to Nominate",
        "description": "Data principal has the right to nominate any other individual to exercise rights under DPDP Act in the event of death or incapacity.",
        "keywords": ["nominate", "nomination", "nominee", "death", "incapacity"],
        "criticality": "LOW",
    },
]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes standard cosine similarity between two dense embedding vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


def _classify_gap(obligation: dict, top_chunk_text: str, similarity_score: float) -> tuple[str, str, str]:
    """Classifies statutory gap: status, severity, and plain-language explanation."""
    title = obligation["title"]
    sec = obligation["section"]
    crit = obligation["criticality"]
    lower = top_chunk_text.lower()

    # Detect explicit disclaimer / negation that indicates absence of protection
    has_disclaimer = any(d in lower for d in ["do not mention", "does not mention", "no mention", "not mention anything"])

    if obligation["id"] == "dpdp_notice":
        has_notice = ("notice" in lower or "itemized" in lower or "collect" in lower) and not has_disclaimer
        has_purpose = "purpose" in lower or "why" in lower or "reason" in lower
        if has_notice and has_purpose:
            return "SATISFIED", "LOW", f"The policy specifies itemized notice of personal data and purposes under {sec}."
        elif has_notice or has_purpose:
            return "PARTIAL", "MEDIUM", f"Notice or purpose is partially stated, but should be more itemized under {sec}."
        else:
            return "MISSING", "HIGH", f"No clear pre-consent notice clause found matching {sec}."

    if obligation["id"] == "dpdp_consent":
        has_consent = "consent" in lower and not has_disclaimer
        has_qual = any(w in lower for w in ["free", "specific", "informed", "unambiguous", "affirmative", "unconditional"])
        if has_consent and has_qual:
            return "SATISFIED", "LOW", f"Consent is framed as free, specific, and affirmative as required by {sec}."
        elif has_consent:
            return "PARTIAL", "MEDIUM", f"Consent is mentioned, but lacks explicit affirmative, unbundled standards under {sec}."
        else:
            return "MISSING", "HIGH", f"No explicit consent mechanism identified under {sec}."

    if obligation["id"] == "dpdp_withdrawal":
        has_withdraw = any(w in lower for w in ["withdraw", "withdrawal", "opt-out", "revoke", "cancel consent"]) and not has_disclaimer
        has_ease = any(w in lower for w in ["settings", "toggle", "one-click", "app", "dashboard", "account", "easily", "anytime"])
        if has_withdraw and has_ease:
            return "SATISFIED", "LOW", f"Provides consent withdrawal mechanisms with ease comparable to consent under {sec}."
        elif has_withdraw:
            return "PARTIAL", "MEDIUM", f"Consent withdrawal is mentioned, but lacks simple in-app one-click ease comparable to giving consent (DPDP Section 6(4))."
        else:
            return "MISSING", "HIGH", f"No easy consent withdrawal mechanism found. DPDP Section 6(4) grants you the statutory right to withdraw consent anytime with ease."

    if obligation["id"] == "dpdp_security":
        has_sec = any(w in lower for w in ["safeguard", "encryption", "tls", "aes", "technical", "organizational"]) or ("security" in lower and not has_disclaimer)
        if has_sec and not has_disclaimer:
            return "SATISFIED", "LOW", f"Enforces reasonable security safeguards and encryption standards under {sec}."
        else:
            return "MISSING", "HIGH", f"No reasonable security safeguards specified. Section 8(5) mandates technical and organizational protection."

    if obligation["id"] == "dpdp_breach_notice":
        has_breach = any(w in lower for w in ["breach", "incident", "security event", "unauthorized access"]) and not has_disclaimer
        has_notify = any(w in lower for w in ["notify", "notification", "intimate", "inform", "report", "72 hours", "72h"])
        if has_breach and has_notify:
            return "SATISFIED", "LOW", f"The policy includes breach notification commitments aligned with {sec}."
        elif has_breach:
            return "PARTIAL", "HIGH", f"The policy mentions security incidents but lacks explicit commitments to notify the Data Protection Board and affected citizens within statutory timelines under {sec}."
        else:
            return "MISSING", "HIGH", f"Non-compliant gap: No breach notification protocol found. Section 8(6) strictly mandates notifying the Data Protection Board and affected users in case of data breaches."

    if obligation["id"] == "dpdp_retention_erasure":
        has_vague = any(w in lower for w in ["as long as needed", "as long as necessary", "at our discretion", "indefinitely", "from time to time"])
        has_erase = any(w in lower for w in ["erase", "erasure", "delete", "deletion", "purge", "anonymize", "30 days"]) and not has_disclaimer
        if has_vague and not has_erase:
            return "PARTIAL", "HIGH", f"The policy uses vague retention terms ('as long as needed/necessary') without clear erasure timelines, which conflicts with Section 8(7) mandatory purpose-bound erasure."
        elif has_erase:
            return "SATISFIED", "LOW", f"The policy provides data deletion and purpose-bound retention limitation aligned with {sec}."
        elif ("retain" in lower or "retention" in lower) and not has_disclaimer:
            return "PARTIAL", "MEDIUM", f"Data retention policies are stated, but specific deletion schedules and purpose-completion erasure could be clearer under {sec}."
        else:
            return "MISSING", "HIGH", f"No clear retention limits or erasure rights specified. Under Section 8(7), data must be erased once the purpose is served."

    if obligation["id"] == "dpdp_children":
        has_child = any(w in lower for w in ["child", "children", "minor", "under 18"]) and not has_disclaimer
        has_parent = any(w in lower for w in ["parental", "guardian", "prohibit", "no tracking", "verifiable"])
        if has_child and has_parent:
            return "SATISFIED", "LOW", f"Addresses children data protections and parental consent under {sec}."
        elif has_child:
            return "PARTIAL", "MEDIUM", f"Mentions age restrictions or minors, but lacks explicit parental consent verification and prohibition on behavioral tracking (Section 9)."
        else:
            return "MISSING", "HIGH", f"No child data protection clauses found. If minors use this service, Section 9 mandates verifiable parental consent and forbids behavioral tracking."

    if obligation["id"] == "dpdp_access_info":
        if ("access" in lower or "summary" in lower or "copy" in lower) and not has_disclaimer:
            return "SATISFIED", "LOW", f"Recognizes citizen right to access summary of personal data under {sec}."
        return "MISSING", "MEDIUM", f"No clause acknowledging the right to access personal data under {sec}."

    if obligation["id"] == "dpdp_correction":
        if ("correct" in lower or "correction" in lower or "update" in lower or "rectify" in lower) and not has_disclaimer:
            return "SATISFIED", "LOW", f"Provides right to correction and updating of personal data under {sec}."
        return "MISSING", "MEDIUM", f"No clause specifying right to correction of inaccurate data under {sec}."

    if obligation["id"] == "dpdp_grievance":
        has_gov = any(w in lower for w in ["grievance", "dpo", "nodal", "officer", "complaint", "redressal"]) and not has_disclaimer
        has_email = bool(re.search(r"[\w\.-]+@[\w\.-]+", top_chunk_text))
        if has_gov and has_email:
            return "SATISFIED", "LOW", f"Identifies a dedicated Grievance Officer / DPO with contact information under {sec}."
        elif has_gov or has_email:
            return "PARTIAL", "MEDIUM", f"Contact email provided, but a dedicated statutory Grievance Officer under Section 13 is not explicitly designated."
        else:
            return "MISSING", "HIGH", f"No designated Grievance Redressal Officer found. Section 13 requires a published grievance contact for citizen complaints."

    if obligation["id"] == "dpdp_nomination":
        if ("nominate" in lower or "nomination" in lower or "nominee" in lower) and not has_disclaimer:
            return "SATISFIED", "LOW", f"Includes right to nominate another individual in case of death or incapacity under {sec}."
        return "MISSING", "LOW", f"Right to nominate under Section 14 is not mentioned."

    # General threshold fallback
    if similarity_score >= 0.58 and not has_disclaimer:
        return "SATISFIED", "LOW", f"Clause strongly matches statutory requirements of {sec} ({title})."
    elif similarity_score >= 0.40 and not has_disclaimer:
        return "PARTIAL", "MEDIUM", f"Clause partially relates to {sec} ({title}), but could be more explicit regarding statutory standards."
    else:
        return "MISSING", crit, f"No adequate clause matching {sec} ({title}) was identified in the policy text."


async def analyze_pdf_similarity(pdf_bytes: bytes, filename: str) -> dict[str, Any]:
    """Performs full cosine similarity check and statutory DPDP gap analysis on an uploaded PDF."""
    t0 = time.time()
    try:
        parsed_doc = parse_document(pdf_bytes, filename, document_id="uploaded_pdf")
    except ValueError:  # no parser extracted meaningful text
        parsed_doc = None
    raw_text = parsed_doc.raw_text if parsed_doc else ""

    if not raw_text.strip():
        return {
            "status": "ERROR",
            "error": "Could not extract enough text from the document. It may be empty, too short, image-only/scanned without OCR, or password protected.",
            "filename": filename,
            "total_pages": parsed_doc.total_pages if parsed_doc else 0,
            "duration_ms": int((time.time() - t0) * 1000),
        }

    # Generate clause chunks
    chunks = clause_aware_chunk(raw_text, source_document=filename, document_type="policy")
    chunk_texts = [c.text for c in chunks]

    # Generate dense embeddings for policy chunks
    chunk_embeddings = generate_embeddings(chunk_texts)

    # Generate dense embeddings for DPDP statutory obligations
    obligation_texts = [f"{o['title']} {o['section']} {o['description']} {' '.join(o['keywords'])}" for o in DPDP_STATUTORY_OBLIGATIONS]
    obligation_embeddings = generate_embeddings(obligation_texts)

    # Compute Cosine Similarity Matrix
    comparison_results = []
    satisfied_count = 0
    partial_count = 0
    missing_count = 0

    for i, ob in enumerate(DPDP_STATUTORY_OBLIGATIONS):
        ob_emb = obligation_embeddings[i]
        best_idx = 0
        best_sim = 0.0
        best_key = (-1, 0.0)

        # Rank chunks by statutory keyword hits first, cosine second: embeddings alone
        # (esp. mock hash vectors) often pick an unrelated clause.
        for j, c_emb in enumerate(chunk_embeddings):
            sim = cosine_similarity(ob_emb, c_emb)
            text_l = chunk_texts[j].lower()
            key = (sum(k in text_l for k in ob["keywords"]), sim)
            if key > best_key:
                best_key, best_sim, best_idx = key, sim, j

        top_chunk = chunks[best_idx] if chunks else None
        top_text = top_chunk.text if top_chunk else ""
        top_section = top_chunk.section if top_chunk else None
        top_page = top_chunk.page_number if top_chunk else 1

        # Classify compliance gap
        status, severity, explanation = _classify_gap(ob, top_text, best_sim)

        if status == "SATISFIED":
            satisfied_count += 1
        elif status == "PARTIAL":
            partial_count += 1
        else:
            missing_count += 1

        # Format excerpt (clean and limited to ~280 chars)
        matched_excerpt = top_text.strip().replace("\n", " ")
        if len(matched_excerpt) > 280:
            matched_excerpt = matched_excerpt[:280] + "..."

        comparison_results.append({
            "obligation_id": ob["id"],
            "dpdp_section": ob["section"],
            "dpdp_title": ob["title"],
            "dpdp_description": ob["description"],
            "criticality": ob["criticality"],
            "status": status,
            "severity": severity,
            "cosine_similarity": round(best_sim, 4),
            "similarity_percentage": f"{int(best_sim * 100)}%",
            "matched_policy_excerpt": matched_excerpt if best_sim >= 0.25 else "No relevant clause found in uploaded document.",
            "policy_page": top_page,
            "policy_section": top_section or "General",
            "plain_language_explanation": explanation,
        })

    # Sort results: MISSING (HIGH) -> PARTIAL -> SATISFIED
    status_order = {"MISSING": 0, "PARTIAL": 1, "SATISFIED": 2}
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    comparison_results.sort(key=lambda x: (status_order.get(x["status"], 3), severity_order.get(x["severity"], 3)))

    # The shared result model (compass.checklist.METHOD): same score and trust indicator as every other view.
    from app.compass.checklist import score as coverage_score, trust as trust_indicator
    dpdp_alignment_score = int(coverage_score([r["status"] for r in comparison_results]))
    trust_score = trust_indicator(dpdp_alignment_score)

    # Actionable Citizen Rights Summary
    citizen_action_items = []
    for item in comparison_results:
        if item["status"] in ("MISSING", "PARTIAL") and item["severity"] in ("HIGH", "MEDIUM"):
            citizen_action_items.append({
                "right": f"Protect against {item['dpdp_title']}",
                "dpdp_basis": item["dpdp_section"],
                "recommendation": item["plain_language_explanation"],
            })

    duration_ms = int((time.time() - t0) * 1000)

    return {
        "status": "SUCCESS",
        "filename": filename,
        "total_pages": parsed_doc.total_pages,
        "total_characters": parsed_doc.total_chars,
        "total_clauses_analyzed": len(chunks),
        "dpdp_alignment_score": dpdp_alignment_score,
        "citizen_trust_score": trust_score,
        "summary_counts": {
            "total_statutory_obligations": len(DPDP_STATUTORY_OBLIGATIONS),
            "satisfied": satisfied_count,
            "partial": partial_count,
            "missing": missing_count,
        },
        "non_compliant_gaps": [r for r in comparison_results if r["status"] in ("MISSING", "PARTIAL")],
        "compliant_clauses": [r for r in comparison_results if r["status"] == "SATISFIED"],
        "all_statutory_comparisons": comparison_results,
        "actionable_citizen_guidance": citizen_action_items[:5],
        "duration_ms": duration_ms,
    }
