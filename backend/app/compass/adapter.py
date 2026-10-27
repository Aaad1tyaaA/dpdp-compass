"""Maps engine output to the response shapes the Compass API and frontend already use."""
from __future__ import annotations

import re

from . import qa, sources
from .audit import GUARDRAILS, get_engine
from .checklist import BY_ID, code

_SEVERITY = {"none": "INFO", "low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "CRITICAL"}
_URGENCY = {"Missing": "IMMEDIATE", "Partial": "SHORT_TERM", "Satisfied": "LOW", "Not applicable": "LOW"}
ACT = "DPDP Act, 2023"
RULES = "DPDP Rules, 2025"


def locate(quote: str, text: str) -> list[int] | None:
    """Character span of a quote in the document text, tolerant of spacing, quotes and punctuation between words."""
    words = re.findall(r"\w+", quote or "")
    if len(words) < 3 or not text:
        return None
    m = re.search(r"\W+".join(map(re.escape, words)), text, re.I)
    return [m.start(), m.end()] if m else None


def findings(report: dict, policy_name: str, policy_text: str | None = None) -> list[dict]:
    engine = get_engine(rules=True)
    out = []
    for i, f in enumerate(report["findings"], 1):
        ob = BY_ID[f["id"]]
        status = f["status"]
        reasoning = {"Satisfied": f"The policy meets the test: {ob['satisfied']}",
                     "Partial": f"The policy only partly meets the obligation: {ob['partial']}",
                     "Missing": "No clause in the policy meets this obligation.",
                     "Not applicable": f"Not applicable to you: {f.get('applicability_reason', '')}"}[status]
        if f.get("penalty_ceiling") and status != "Satisfied":
            reasoning += f" Penalty ceiling in the Schedule: {f['penalty_ceiling']}"
        page = engine.provision_page(f["provision"])
        legal = {"id": f"DPDP-{f['provision']}", "source_document": ACT, "section": f"Section {f['provision']}", "clause": None, "page": page,
                 "text": f.get("statute", ""), "type": "LEGAL", "url": sources.file_url("dpdp-act-2023", page)}
        span = locate(f.get("quote", ""), policy_text or "")
        policy_ev = [{"citation": {"id": f"POL-{f['id']}", "source_document": policy_name, "section": None, "clause": None, "page": None,
                                   "text": f["quote"], "type": "POLICY", "span": span}, "excerpt": f["quote"], "relevance_score": float(f.get("confidence", 0.5))}] if f.get("quote") else []
        out.append({
            "id": f"f_{i}", "obligation_id": f["id"], "obligation_title": ob["title"], "obligation_description": ob["satisfied"],
            "principle": (f.get("principle") or "").title(), "status": code(status), "severity": _SEVERITY.get(f.get("risk", "low"), "LOW"),
            "urgency": _URGENCY[status], "reasoning": reasoning, "policy_evidence": policy_ev,
            "legal_evidence": [{"citation": legal, "excerpt": f.get("statute", "")[:600], "relevance_score": 1.0}] if f.get("citation") else [],
            "confidence": float(f.get("confidence", 0.5)),
            "recommended_action": "No action needed while your answers stay true." if status == "Not applicable"
            else "Keep this wording and make sure practice matches it." if status == "Satisfied"
            else f"Add or strengthen a clause so that it does the following. {ob['satisfied']} ({ACT}, Section {f['provision']})",
            "fixes": f.get("fixes", []) if status not in ("Satisfied", "Not applicable") else [],
            "rule_checks": f.get("rule_checks", []), "decided_by": f.get("decided_by", "judge"),
            "suggested_rewrite": f.get("example") if status not in ("Satisfied", "Not applicable") else None, "guardrail_flags": f.get("guardrail_flags", []), "exemptions": f.get("exemptions", []),
            "in_force_from": f.get("in_force_from"), "legal_status": f.get("legal_status"), "assessed_on": f.get("assessed_on"),
            "conflicts": f.get("conflicts", []), "support": f.get("support"),
            "passages": [{"text": t, "span": locate(t, policy_text or "")} for t in f.get("passages", [])],
            "rules": [{**r, "page": sources.page_of(r["provision"]), "url": sources.file_url("dpdp-rules-2025", sources.page_of(r["provision"]))}
                      for r in f.get("rules", [])], "applies": f.get("applies", True), "model_status": code(f.get("model_status") or status),
        })
    return out


def guardrail_results(report: dict) -> list[dict]:
    out = []
    for gid, rule, action in GUARDRAILS:
        hit = [f["id"] for f in report["findings"] if gid in f.get("guardrail_flags", [])]
        out.append({"id": gid, "rule": rule, "passed": not hit, "severity": "MEDIUM" if hit else "INFO",
                    "reason": f"Triggered on {', '.join(hit)}. Action: {action}." if hit else "No finding failed this check.",
                    "violated_rule": gid if hit else None, "recommendation": action if hit else None})
    return out


def evidence(hits: list[dict]) -> list[dict]:
    """Engine retrieval hits as the RetrievedEvidence fields the existing agents consume."""
    out = []
    for h in hits:
        prov = h.get("provisions", [])
        label = "Schedule" if h["id"] == "schedule" else qa.label(prov[0]) if prov else h.get("title", "")
        doc = RULES if h.get("source") else ACT
        out.append({"chunk_id": h["id"], "text": h["text"], "source_document": doc, "section": f"Section {h['section']}" if h.get("section") else label,
                    "clause": prov[0] if prov else None, "page": h.get("page") or None, "citation": f"{doc}, {label}",
                    "score": max(0.36, 1.0 - 0.06 * (h["rank"] - 1)), "type": "vector",
                    "metadata": {"provisions": prov, "title": h.get("title"), "chapter": h.get("chapter"), "retrievers": h.get("sources", []), "in_force_from": sources.status(prov[0])["in_force_from"] if prov else None}})
    return out


def kb_stats() -> dict:
    e = get_engine(rules=True)
    lengths = [len(c["text"]) for c in e.chunks]
    return {"statute": e.st.name, "sections": len(e.st.sections), "chunks": len(e.chunks), "mean_chunk_chars": round(sum(lengths) / len(lengths)),
            **e.kb.counts()}
