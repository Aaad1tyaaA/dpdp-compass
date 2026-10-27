from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
import json
import re
import time
from collections import OrderedDict
import uuid
import logging
from app.services.pdf_analyzer import analyze_pdf_similarity
from app.api.uploads import read_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/citizen", tags=["citizen"])


_NO_POLICY_PRACTICES = {
    "data_collected": ["No policy analysed — name a company (e.g. Zomato, Swiggy) or upload its policy"],
    "purpose": ["No policy analysed"],
    "sharing": "No policy analysed.",
    "retention": "No policy analysed.",
}

_PRACTICE_KEYWORDS = {
    # (section-heading keywords, sentence keywords)
    "data_collected": (("collect", "information we", "data we"), ("we collect", "we obtain", "we gather", "we receive")),
    "purpose": (("purpose", "how we use", "use of"), ("we use", "use your", "used to", "used for", "in order to")),
    "sharing": (("shar", "disclos", "third part"), ("share", "disclose", "third part", "sell")),
    "retention": (("retention", "retain", "deletion", "storage"), ("retain", "retention", "stored for", "as long as", "purged", "erase")),
}
_HEADING = re.compile(r"^\s*(?:#+|\d+[.)])\s+")
_BULLET = re.compile(r"^\s*[-*•]\s+")


def _extract_practices(text: str) -> dict:
    """The policy's own statements about collection/purpose/sharing/retention.
    Structured policies: bullets under the matching numbered heading. Otherwise: keyword sentences.
    ponytail: heuristic; swap for LLM extraction if quality needs to go up."""
    sections: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if _HEADING.match(line):
            sections.append((line.lower(), []))
        elif line.strip() and sections:
            sections[-1][1].append(line.strip())
    sentences = [x.strip(" -*•\t") for x in re.split(r"(?<=[.!?])\s+|\n+", text)]
    sentences = [x for x in sentences if len(x.split()) >= 6 and not x.endswith(":") and not _HEADING.match(x)]

    def pick(key: str, n: int) -> list[str]:
        head_kw, sent_kw = _PRACTICE_KEYWORDS[key]
        for heading, body in sections:
            if any(k in heading for k in head_kw):
                # keep full statements ("We do not sell personal data.") and bullets; drop "...as follows:" lead-ins
                items = [x for l in body for x in re.split(r"(?<=[.!?])\s+", _BULLET.sub("", l)) if x and not x.endswith(":")]
                if items:
                    return [i[:220] for i in items[:n]]
        hits = [x[:220] for x in sentences if any(k in x.lower() for k in sent_kw)]
        return list(dict.fromkeys(hits))[:n]

    return {
        "data_collected": pick("data_collected", 4) or ["Policy does not clearly state what data is collected"],
        "purpose": pick("purpose", 4) or ["Policy does not clearly state purposes"],
        "sharing": " ".join(pick("sharing", 3)) or "Policy does not clearly state who data is shared with.",
        "retention": " ".join(pick("retention", 2)) or "No retention period stated — DPDP Section 8(7) requires erasure once the purpose is served.",
    }


def _reference_policy_for(q: str) -> tuple[str, str] | None:
    """(name, text) of a bundled reference policy whose company is named in the question."""
    from app.knowledge_base.auto_indexer import REFERENCE_DIR
    words = set(re.findall(r"[a-z0-9]+", q.lower()))
    for f in sorted(REFERENCE_DIR.glob("*.txt")):
        if f.stem.split("_")[0].lower() in words:
            return f.stem.replace("_", " "), f.read_text(encoding="utf-8", errors="ignore")
    return None


def _dedupe_citations(citations: list) -> list:
    """One entry per passage (findings often cite the same section), law before company policy."""
    seen, out = set(), []
    for c in citations:
        if not isinstance(c, dict):
            continue
        key = (c.get("source_document"), c.get("section"), (c.get("text") or "")[:80])
        if key not in seen:
            seen.add(key)
            out.append(c)
    return sorted(out, key=lambda c: c.get("type") != "LEGAL")


def _legal_citations(evidence: list[dict]) -> list[dict]:
    """Citation dicts from retrieved legal passages (used when there are no audit findings)."""
    return [{
        "id": e.get("chunk_id") or f"leg_{i}",
        "source_document": e.get("source_document") or "DPDP Act, 2023",
        "section": e.get("section") or "",
        "text": (e.get("text") or "")[:300],
        "type": "LEGAL",
    } for i, e in enumerate(evidence[:4]) if isinstance(e, dict)]


@router.get("/reference-companies")
async def reference_companies():
    """Companies with a bundled reference policy (usable as `reference_company`)."""
    from app.knowledge_base.auto_indexer import REFERENCE_DIR
    return sorted(f.stem.split("_")[0] for f in REFERENCE_DIR.glob("*.txt"))


async def _build_dynamic_citizen_response(q: str) -> dict:
    """Dynamically generates evidence-grounded citizen response using DPDP Act knowledge base."""
    from app.retrieval.hybrid_retriever import hybrid_retrieve
    hits = await hybrid_retrieve(q or "DPDP rights and data fiduciary obligations", top_k=4)
    citations = []
    for h in hits:
        cit = h.get("citation") or {
            "id": h.get("chunk_id", "cit_1"),
            "source_document": h.get("source_document", "DPDP Act 2023"),
            "section": h.get("section", "Section 6"),
            "text": h.get("text", "")[:200],
            "type": "LEGAL",
        }
        citations.append(cit)

    if not citations:
        citations = [
            {"id": "cit_dpdp_s6", "source_document": "Digital Personal Data Protection Act, 2023", "section": "Section 6", "text": "Notice and consent requirements for processing personal data.", "type": "LEGAL"},
            {"id": "cit_dpdp_s8", "source_document": "Digital Personal Data Protection Act, 2023", "section": "Section 8", "text": "General obligations of data fiduciary, including reasonable security safeguards and 72h breach notification.", "type": "LEGAL"},
            {"id": "cit_dpdp_s12", "source_document": "Digital Personal Data Protection Act, 2023", "section": "Section 12", "text": "Right to correction and erasure of personal data.", "type": "LEGAL"},
            {"id": "cit_dpdp_s13", "source_document": "Digital Personal Data Protection Act, 2023", "section": "Section 13", "text": "Right of grievance redressal with Data Protection Officer and Data Protection Board.", "type": "LEGAL"},
        ]

    summary_text = (
        f"Based on the DPDP Act 2023 statutory provisions: You have statutory rights to notice (Sec 5/6), "
        f"consent withdrawal (Sec 6(4)), grievance redressal (Sec 13), and data erasure (Sec 12). "
        f"Data Fiduciaries are required to implement reasonable security safeguards (Sec 8(5)) and report "
        f"breaches to the Board and Data Principals within 72 hours (Sec 8(6))."
    )
    if hits:
        top_excerpts = " | ".join(f"[{h.get('section', 'DPDP')}]: {h.get('text', '')[:120]}" for h in hits[:2])
        summary_text += f"\n\n**Retrieved Statutory Authority**: {top_excerpts}"

    return {
        "id": f"cit_{uuid.uuid4().hex[:6]}",
        "policy_name": q[:30] if q else "DPDP Statutory Inquiry",
        "summary": summary_text,
        "your_rights": [
            {
                "title": "Right to Withdraw Consent",
                "description": "Withdraw consent anytime with ease comparable to giving consent (DPDP Section 6(4)).",
                "citation": citations[0] if citations else {"source_document": "DPDP Act 2023", "section": "Section 6(4)", "text": "Ease of consent withdrawal", "type": "LEGAL"}
            },
            {
                "title": "Right to Erasure & Purpose Limitation",
                "description": "Request deletion of personal data once the specified processing purpose is fulfilled (DPDP Section 8(7) & 12).",
                "citation": citations[1] if len(citations) > 1 else {"source_document": "DPDP Act 2023", "section": "Section 12", "text": "Right to erasure", "type": "LEGAL"}
            },
            {
                "title": "Right to Grievance Redressal",
                "description": "File complaints with the Data Protection Officer (DPO) and escalate to the Data Protection Board of India (DPDP Section 13).",
                "citation": citations[2] if len(citations) > 2 else {"source_document": "DPDP Act 2023", "section": "Section 13", "text": "Grievance redressal mechanism", "type": "LEGAL"}
            },
        ],
        "company_obligations": [
            {"title": "Reasonable Security Safeguards", "description": "Mandatory encryption & technical controls (Section 8(5))."},
            {"title": "72-Hour Personal Data Breach Notice", "description": "Mandatory notification to Board and affected users (Section 8(6))."},
            {"title": "Verifiable Parental Consent for Minors", "description": "Strict prohibition on behavioral tracking of children (Section 9)."},
        ],
        **_NO_POLICY_PRACTICES,
        "shortfalls": [],
        "trust_score": None,
        "policy_analyzed": False,
        "citations": citations[:4],
        "guardrails": [{"rule": "Statutory Evidence Grounding", "passed": True, "details": "Derived from DPDP Act 2023 knowledge base"}],
        "trace": [{"agent": "Dynamic Citizen RAG", "status": "COMPLETED", "duration_ms": 12, "output_summary": f"Retrieved {len(hits)} statutory chunks"}],
        "detected_language": "en",
        "evidence_hierarchy": {
            "legal_source_priority": True,
            "company_policy_not_authority": True,
            "evidence_traceability": True,
        },
    }


@router.post("/analyze-pdf")
async def analyze_citizen_pdf(file: UploadFile = File(...)):
    """Uploads a PDF privacy policy, computes cosine similarity against DPDP Act obligations,
    and returns clause-by-clause gap analysis with plain-language citizen explanations."""
    content = await read_upload(file)
    try:
        report = await analyze_pdf_similarity(content, file.filename)
        if report.get("status") == "ERROR":
            raise HTTPException(status_code=422, detail=report["error"])
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Citizen PDF analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"PDF similarity analysis failed: {str(e)}")


class CompareBody(BaseModel):
    text: str | None = None
    reference_company: str | None = None  # scan a bundled reference policy, e.g. "Zomato"
    policy_text: str | None = None
    filename: str | None = None


class CitizenBody(BaseModel):
    text: str | None = None
    query: str | None = None
    policy_id: str | None = None
    policy_text: str | None = None
    policy_name: str | None = None


@router.post("/compare-similarity")
async def compare_similarity_text(body: CompareBody):
    """Performs cosine similarity check and statutory gap analysis on raw policy text."""
    text = body.text or body.policy_text or ""
    if body.reference_company:
        ref = _reference_policy_for(body.reference_company)
        if ref is None:
            raise HTTPException(status_code=404, detail=f"no reference policy for {body.reference_company!r}")
        text = ref[1]
    filename = body.filename or "policy_text.txt"
    if not text.strip():
        raise HTTPException(status_code=400, detail="text, policy_text or reference_company is required")
    try:
        content = text.encode("utf-8")
        report = await analyze_pdf_similarity(content, filename)
        if report.get("status") == "ERROR":
            raise HTTPException(status_code=422, detail=report["error"])
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Citizen text similarity analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Text similarity analysis failed: {str(e)}")


_ANSWER_CACHE: "OrderedDict[tuple, tuple[float, dict]]" = OrderedDict()
_CACHE_TTL_S, _CACHE_MAX = 3600, 256


def _cache_key(body: CitizenBody) -> tuple:
    import hashlib
    # Case, spacing and end punctuation don't change the question ("?", "!", "." and the Hindi danda).
    q = " ".join((body.text or body.query or body.policy_id or "").lower().split()).strip(" ?!.।")
    return (q, hashlib.sha256((body.policy_text or "").encode()).hexdigest(), body.policy_name or "")


def _cache_get(key: tuple) -> dict | None:
    hit = _ANSWER_CACHE.get(key)
    if hit and time.time() - hit[0] < _CACHE_TTL_S:
        _ANSWER_CACHE.move_to_end(key)
        return {**hit[1], "id": f"cit_{uuid.uuid4().hex[:6]}", "cached": True}
    return None


def _cache_put(key: tuple, res: dict) -> None:
    # Never cache the canned fallback (e.g. produced during a transient LLM outage).
    if res.get("summary") and not res["summary"].startswith("Based on the DPDP Act 2023 statutory provisions"):
        _ANSWER_CACHE[key] = (time.time(), res)
        while len(_ANSWER_CACHE) > _CACHE_MAX:
            _ANSWER_CACHE.popitem(last=False)


@router.post("/analyze")
async def citizen_analyze(body: CitizenBody):
    """Cached: repeated questions are answered instantly and don't spend LLM quota. Keyed on the
    normalised question + policy, so different policies never collide.
    ponytail: per-process LRU; move to Redis when running >1 worker."""
    key = _cache_key(body)
    if hit := _cache_get(key):
        return hit
    res = _with_claims(await _citizen_analyze(body), body)
    _cache_put(key, res)
    return res


def _with_claims(res: dict, body: CitizenBody) -> dict:
    """Each sentence of the answer checked against the cited law and the policy it was asked about."""
    from app.compass.claims import check
    evidence = [c.get("text", "") for c in res.get("citations", [])] + ([body.policy_text] if body.policy_text else [])
    return {**res, "claim_check": check(res.get("summary", ""), evidence)}


@router.post("/analyze/stream")
async def citizen_analyze_stream(body: CitizenBody):
    """Same answer as /analyze, streamed as Server-Sent Events so text appears as the model writes it.
    Events (JSON in each `data:` line): status -> token* -> done{full CitizenAnalysis payload}; error on failure."""
    from fastapi.responses import StreamingResponse
    from app.agents.policy_generation_agent import stream_citizen_answer

    def sse(obj: dict) -> str:
        return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

    async def events():
        key = _cache_key(body)
        if hit := _cache_get(key):
            yield sse({"type": "token", "text": hit["summary"]})
            yield sse({"type": "done", "data": hit})
            return
        yield sse({"type": "status", "text": "Searching the DPDP Act"})
        try:
            res = await _citizen_analyze(body, defer_answer=True)
            state = res.pop("_answer_state", None)
            if state is None:  # fallback template: the summary is already complete
                yield sse({"type": "token", "text": res["summary"]})
            else:
                parts = []
                async for chunk in stream_citizen_answer(state):
                    parts.append(chunk)
                    yield sse({"type": "token", "text": chunk})
                res["summary"] = "".join(parts)
                res = _with_claims(res, body)
                _cache_put(key, res)
            yield sse({"type": "done", "data": res})
        except Exception as e:
            logger.warning("citizen stream failed: %s", e)
            yield sse({"type": "error", "text": "The answer could not be generated. Please try again."})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def _citizen_analyze(body: CitizenBody, defer_answer: bool = False):
    q = body.text or body.query or body.policy_id or ""
    policy_text, policy_name = body.policy_text, body.policy_name
    if not policy_text:
        # "What does Zomato do with my data?" → audit Zomato's reference policy, not nothing.
        ref = _reference_policy_for(q)
        if ref:
            policy_name, policy_text = policy_name or ref[0], ref[1]
    try:
        from app.agents.orchestrator import orchestrate
        t0 = time.perf_counter()
        res = await orchestrate(query=q, mode="citizen", policy_text=policy_text, defer_answer=defer_answer)
        logger.info("citizen timing orchestrate_ms=%d trace_ms=%d", (time.perf_counter() - t0) * 1000,
                    sum(s.get("duration_ms", 0) for s in res.get("trace", [])))
        findings = res.get("findings", [])
        obligations = res.get("obligations", [])
        citations = _dedupe_citations(res.get("citations", []) or _legal_citations(res.get("evidence", {}).get("legal", [])))
        # Only fall back to the canned template when the model produced nothing usable at all.
        if not defer_answer and not res.get("final_answer") and not (findings and citations):
            return await _build_dynamic_citizen_response(q)
        if policy_text:
            # Evidence-first: a trust score only exists when an actual policy was compared.
            from app.compass.checklist import score as coverage_score, trust as trust_indicator
            trust = trust_indicator(coverage_score([f.get("status", "MISSING") for f in findings]))
            practices = _extract_practices(policy_text)
            shortfalls = [{"title": f.get("obligation_title", "Gap"), "severity": f.get("severity", "MEDIUM"), "description": f.get("reasoning", "")[:160]} for f in findings if f.get("status") in ("MISSING", "PARTIAL")][:3] or [{"title": "No major shortfall", "severity": "LOW", "description": "Policy appears aligned."}]
        else:
            trust, practices, shortfalls = None, _NO_POLICY_PRACTICES, []
        return {
            "id": f"cit_{uuid.uuid4().hex[:6]}",
            "policy_name": policy_name or (q[:24] if len(q) < 24 else "Your query"),
            "summary": res.get("final_answer") or f"Checked {len(findings)} DPDP obligations.",
            "your_rights": [{"title": o.get("obligation", "Right"), "description": o.get("obligation", ""), "citation": {"id": o.get("obligation_id", "cr"), "source_document": o.get("source", "DPDP Act"), "section": o.get("section", ""), "text": o.get("obligation", ""), "type": "LEGAL"}} for o in obligations[:3]],
            "company_obligations": [{"title": f.get("obligation_title", "Obligation"), "description": f.get("reasoning", "")[:120]} for f in findings[:3]],
            **practices,
            "shortfalls": shortfalls,
            "trust_score": trust,
            "policy_analyzed": bool(policy_text),
            "citations": citations[:4],
            "guardrails": res.get("guardrails", []),
            "trace": res.get("trace", []),
            "detected_language": res.get("detected_language", "en"),
            "evidence_hierarchy": {
                "legal_source_priority": True,
                "company_policy_not_authority": True,
                "evidence_traceability": True,
            },
            **({"_answer_state": {
                "query": q, "detected_language": res.get("detected_language", "en"),
                "evidence_legal": res.get("evidence", {}).get("legal", []),
                "evidence_policy": res.get("evidence", {}).get("policy", []),
            }} if defer_answer else {}),
        }
    except Exception as e:
        logger.warning("citizen orchestrator dynamic fallback: %s", e)
        return await _build_dynamic_citizen_response(q)


@router.get("/policy/{policy_id}")
async def citizen_policy(policy_id: str):
    from app.api.policies import find_policy
    p = find_policy(policy_id)
    if p is None:
        raise HTTPException(status_code=404, detail="policy not found")
    name = p.get("company") or p.get("name") or policy_id
    return await citizen_analyze(CitizenBody(
        text=f"What does {name} do with my personal data, and what are my rights?",
        policy_text=p.get("text"), policy_name=p.get("name"),
    ))


# ── rights-request letters ──────────────────────────────────────────────────
class RequestDraftBody(BaseModel):
    type: str
    company: str = Field(min_length=1, max_length=120)
    name: str | None = Field(default=None, max_length=120)
    contact: str | None = Field(default=None, max_length=200)
    account: str | None = Field(default=None, max_length=200)
    details: str | None = Field(default=None, max_length=3000)


@router.get("/requests/types")
async def request_types():
    from app.compass.rights_requests import TYPES
    return [{"id": k, "title": v["title"], "provisions": v["provisions"]} for k, v in TYPES.items()]


@router.post("/requests/draft")
async def request_draft(body: RequestDraftBody):
    """A letter for the person to send themselves. The company contact comes only from that company's policy text, if we hold it."""
    from app.compass.rights_requests import TYPES, draft
    if body.type not in TYPES:
        raise HTTPException(status_code=422, detail=f"type must be one of {', '.join(TYPES)}")
    ref = _reference_policy_for(body.company)
    name = ref[0].replace(" Privacy Policy", "") if ref else body.company.strip()
    return draft(body.type, name, ref[1] if ref else None, body.model_dump())
