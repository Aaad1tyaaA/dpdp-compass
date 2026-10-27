from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import date, datetime
from pathlib import Path
import contextvars
import json
import os
import sqlite3
import uuid
import logging
from app.compass.checklist import METHOD
from app.evaluation.registry import run_all

logger = logging.getLogger(__name__)
current_uid: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_uid", default=None)
router = APIRouter(prefix="/api/compliance", tags=["compliance"])


class _AnalysisStore:
    """Dict-like store persisted to SQLite so analyses survive restarts.
    ponytail: single-file SQLite; move to the Postgres `Analysis` model once Postgres is always-on."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
        # Reviewer decisions are an append-only trail beside the model's output, which is never rewritten.
        self._db.execute("""CREATE TABLE IF NOT EXISTS review_events (seq INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id TEXT NOT NULL,
            finding_id TEXT NOT NULL, decision TEXT NOT NULL, status TEXT, note TEXT, user_id TEXT, user_name TEXT, at TEXT NOT NULL)""")
        self._lock = __import__("threading").Lock()
        if "owner" not in [r[1] for r in self._db.execute("PRAGMA table_info(analyses)")]:
            self._db.execute("ALTER TABLE analyses ADD COLUMN owner TEXT")  # audits saved before accounts existed have no owner
        self._db.commit()

    # Every read and write is scoped to the signed-in user (current_uid, set per request). With no
    # user (auth disabled, or a service call with the API key) nothing is filtered.
    def __setitem__(self, key: str, value: dict):
        self._db.execute("INSERT OR REPLACE INTO analyses (id, body, owner) VALUES (?, ?, ?)", (key, json.dumps(value, default=str), current_uid.get()))
        self._db.commit()

    def recent(self, limit: int = 20) -> list[dict]:
        uid = current_uid.get()
        rows = self._db.execute("SELECT body FROM analyses WHERE (? IS NULL OR owner = ?) ORDER BY rowid DESC LIMIT ?", (uid, uid, limit)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get(self, key: str, default=None):
        uid = current_uid.get()
        row = self._db.execute("SELECT body FROM analyses WHERE id = ? AND (? IS NULL OR owner = ?)", (key, uid, uid)).fetchone()
        return json.loads(row[0]) if row else default

    def events(self, aid: str) -> list[dict]:
        cols = ("seq", "finding_id", "decision", "status", "note", "user_name", "at")
        return [dict(zip(cols, r)) for r in self._db.execute(
            f"SELECT {', '.join(cols)} FROM review_events WHERE analysis_id = ? ORDER BY seq", (aid,))]

    def review(self, aid: str, expected_rev: int, event: dict) -> int:
        """Append a decision if nobody else has reviewed since expected_rev (optimistic concurrency); returns the new rev."""
        with self._lock:
            rev = self._db.execute("SELECT COUNT(*) FROM review_events WHERE analysis_id = ?", (aid,)).fetchone()[0]
            if rev != expected_rev:
                raise ValueError(rev)
            self._db.execute("INSERT INTO review_events (analysis_id, finding_id, decision, status, note, user_id, user_name, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (aid, event["finding_id"], event["decision"], event.get("status"), event.get("note"), event.get("user_id"),
                              event.get("user_name"), datetime.utcnow().isoformat() + "Z"))
            self._db.commit()
            return rev + 1

    def delete_user(self, uid: str) -> None:
        self._db.execute("DELETE FROM review_events WHERE analysis_id IN (SELECT id FROM analyses WHERE owner = ?)", (uid,))
        self._db.execute("DELETE FROM analyses WHERE owner = ?", (uid,))
        self._db.commit()


ANALYSES = _AnalysisStore(Path(os.getenv("ANALYSES_DB") or Path(__file__).resolve().parents[2] / "storage" / "analyses.db"))


class AnalyzeBody(BaseModel):
    policy_id: str = "pol_1"
    text: str | None = None
    policy_text: str | None = None
    policy_name: str | None = None
    reference_company: str | None = None  # audit a bundled reference policy, e.g. "Zomato"
    as_of: date | None = None  # assessment date for "in force" statuses; default today
    version: int | None = None  # version of a saved policy to audit; default latest
    applicability: dict[str, str] | None = None  # answers to compass.applicability.QUESTIONS


def _counts(findings: list[dict]):
    from collections import Counter
    sev = Counter(f.get("severity","INFO") for f in findings)
    stat = Counter(f.get("status","MISSING") for f in findings)
    for k in ["CRITICAL","HIGH","MEDIUM","LOW","INFO"]: sev.setdefault(k,0)
    for k in ["SATISFIED","PARTIAL","MISSING","NOT_APPLICABLE"]: stat.setdefault(k,0)
    return dict(sev), dict(stat)

def _score(findings: list[dict]) -> int:
    from app.compass.checklist import score  # the shared result model; NOT_APPLICABLE is excluded there
    return int(score([f.get("status", "MISSING") for f in findings]))

@router.get("")
async def list_analyses(limit: int = 20):
    return [{k: a.get(k) for k in ("id", "policy_id", "policy_name", "created_at", "overall_score", "status")} for a in ANALYSES.recent(min(limit, 100))]

def _input_notes(text: str, findings: list[dict]) -> list[str]:
    """Ask for more when the text looks like a fragment, instead of quietly scoring it low."""
    words, missing = len(text.split()), [f["obligation_title"] for f in findings if f["status"] == "MISSING"]
    notes = []
    if words < 300:
        notes.append(f"This text has only {words} words; a full privacy policy usually has well over a thousand. If it is an excerpt, "
                     "upload or paste the whole policy so the score is fair.")
    if len(missing) >= 7:
        notes.append(f"{len(missing)} obligations found nothing in the text ({', '.join(missing[:4])}…). If these are covered in another "
                     "document (terms of use, a consent screen, a grievance page), add that text and audit again.")
    return notes


@router.post("/analyze")
async def analyze(body: AnalyzeBody):
    policy_id = body.policy_id
    policy_text = body.text or body.policy_text or ""
    policy_name = body.policy_name or f"Policy Audit ({policy_id})"
    if body.reference_company:
        from app.api.citizen import _reference_policy_for
        ref = _reference_policy_for(body.reference_company)
        if ref is None:
            raise HTTPException(status_code=404, detail=f"no reference policy for {body.reference_company!r}")
        policy_name, policy_text = body.policy_name or ref[0], ref[1]
        policy_id = f"ref_{body.reference_company.lower()}"
    # Every audit of the caller's own text names the document version it read (reference policies are not stored).
    from app.api.policies import DOCUMENTS, find_policy
    doc = None
    if not body.reference_company:
        if not policy_text:  # an uploaded or saved policy: use its stored text
            doc = find_policy(policy_id, body.version)
            policy_text = doc["text"] if doc else ""  # not found (or not the caller's): rejected below as empty
        elif len(policy_text.strip()) >= 50:  # pasted text becomes (or matches) a saved policy
            saved = DOCUMENTS.find_by_text(policy_text) or DOCUMENTS.create(body.policy_name or "Pasted policy", policy_text, "paste")
            doc = find_policy(saved["id"])
        if doc:
            policy_id, policy_name = doc["id"], body.policy_name or doc["name"]
    aid = f"ana_{uuid.uuid4().hex[:6]}"

    # The audit runs on the Compass engine: 14-obligation checklist, per-obligation policy clauses,
    # citations attached from the knowledge base, guardrails on the output (app/compass).
    import asyncio
    from app.compass import adapter, workflow
    if len(policy_text.strip()) < 50:
        raise HTTPException(status_code=422, detail="policy text is empty or too short to audit")
    report = await asyncio.to_thread(workflow.run, "", policy_text, "auto", body.as_of, body.applicability)
    findings = adapter.findings(report, policy_name, policy_text)
    res = {"trace": report["trace"], "guardrails": adapter.guardrail_results(report),
           "citations": [f["legal_evidence"][0]["citation"] for f in findings if f["legal_evidence"]],
           "risks": [{"obligation_id": f["obligation_id"], "severity": f["severity"], "urgency": f["urgency"]} for f in findings if f["status"] != "SATISFIED"],
           "evidence": {"judge": report["judge"], "engine_score": report["score"], "degraded": report.get("degraded")}, "top_k": 3}
    analysis = {
        "id": aid, "policy_id": policy_id, "policy_name": policy_name,
        "created_at": datetime.utcnow().isoformat()+"Z", "status":"COMPLETED", "overall_score": _score(findings),
        "findings": findings,
        "severity_counts": _counts(findings)[0],
        "status_counts": _counts(findings)[1],
        "agent_trace": res.get("trace") or [],
        "guardrail_results": res.get("guardrails") or [],
        "citations": res.get("citations", []),
        "risks": res.get("risks", []),
        "evidence": res.get("evidence", {}),
        "top_k": res.get("top_k", 8),
        "input_notes": _input_notes(policy_text, findings),
        "method": METHOD, "applicability": report.get("applicability"), "conflicts": report.get("conflicts", []), "assessed_on": report.get("assessed_on"), "sources": report.get("sources", []),
        "reference_text": policy_text if body.reference_company else None,  # public text, so the evidence viewer can show it
        "document": {"id": doc["id"], "name": doc["name"], "version": doc["version"], "sha256": doc["sha256"], "source": doc["source"]} if doc else None,
    }
    logger.info("compliance analyze business findings=%d", len(findings))
    ANALYSES[aid]=analysis
    return _with_reviews(analysis)

def _get(analysis_id: str) -> dict:
    a = ANALYSES.get(analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return _with_reviews(a)


def _with_reviews(a: dict) -> dict:
    """Each finding gets its latest reviewer decision; the reviewed score uses a reviewer's status where one was set."""
    from app.compass.checklist import score
    events = ANALYSES.events(a["id"])
    latest = {e["finding_id"]: e for e in events if e["decision"] in ("accept", "override", "clear")}
    for f in a["findings"]:
        e = latest.get(f["id"])
        f["review"] = None if e is None or e["decision"] == "clear" else e
    effective = [(f["review"] or {}).get("status") or f["status"] for f in a["findings"]]
    reviewed = sum(f["review"] is not None for f in a["findings"])
    return {**a, "review_rev": len(events), "activity": events[::-1][:50], "reviewed_count": reviewed,
            "reviewed_score": int(score(effective)) if reviewed else None}


class ReviewBody(BaseModel):
    decision: str            # accept | override | clear
    status: str | None = None  # with override: SATISFIED | PARTIAL | MISSING | NOT_APPLICABLE
    note: str | None = None
    rev: int                 # review_rev the reviewer saw; a stale value is rejected with 409


@router.post("/{analysis_id}/findings/{finding_id}/review")
async def review_finding(analysis_id: str, finding_id: str, body: ReviewBody, request: Request):
    a = _get(analysis_id)
    if not any(f["id"] == finding_id for f in a["findings"]):
        raise HTTPException(status_code=404, detail="finding not found")
    if body.decision not in ("accept", "override", "clear"):
        raise HTTPException(status_code=422, detail="decision must be accept, override or clear")
    if body.decision == "override" and body.status not in ("SATISFIED", "PARTIAL", "MISSING", "NOT_APPLICABLE"):
        raise HTTPException(status_code=422, detail="an override needs a status")
    if body.decision == "override" and not (body.note or "").strip():
        raise HTTPException(status_code=422, detail="an override needs a reason")
    user = getattr(request.state, "user", None) or {}
    try:
        ANALYSES.review(analysis_id, body.rev, {"finding_id": finding_id, "decision": body.decision,
                                                "status": body.status if body.decision == "override" else None,
                                                "note": (body.note or "").strip()[:2000] or None,
                                                "user_id": user.get("id"), "user_name": user.get("name") or user.get("email")})
    except ValueError:
        raise HTTPException(status_code=409, detail="someone else reviewed this audit since you loaded it; reload and try again")
    return _get(analysis_id)

# ── redlining, re-audit and comparison ──────────────────────────────────────
_RANK = {"MISSING": 0, "PARTIAL": 1, "SATISFIED": 2}


def compare(a: dict, b: dict) -> dict:
    """What changed between two audits: each obligation's status, the text, and whether the two are comparable at all."""
    differences = [label for label, key in (("scoring method", lambda x: (x.get("method") or {}).get("version")),
                                            ("legal sources", lambda x: [s.get("gazette") for s in x.get("sources") or []]),
                                            ("assessment date", lambda x: x.get("assessed_on")),
                                            ("applicability answers", lambda x: (x.get("applicability") or {}).get("answers")))
                   if key(a) != key(b)]
    fb = {f["obligation_id"]: f for f in b["findings"]}
    changes = []
    for f in a["findings"]:
        g = fb.get(f["obligation_id"])
        if g is None or g["status"] == f["status"]:
            continue
        ra, rb = _RANK.get(f["status"]), _RANK.get(g["status"])
        kind = "scope" if ra is None or rb is None else "improved" if rb > ra else "regressed"
        changes.append({"obligation_id": f["obligation_id"], "title": f["obligation_title"], "from": f["status"], "to": g["status"], "change": kind})
    text = []
    da, db = a.get("document") or {}, b.get("document") or {}
    if da.get("id") and da.get("id") == db.get("id"):
        from app.api.policies import DOCUMENTS
        from app.compass.redline import diff
        ta, tb = DOCUMENTS.text(da["id"], da["version"]), DOCUMENTS.text(db["id"], db["version"])
        text = diff(ta or "", tb or "")
    return {"a": {"id": a["id"], "version": da.get("version"), "score": a["overall_score"]},
            "b": {"id": b["id"], "version": db.get("version"), "score": b["overall_score"]},
            "comparable": not differences, "differences": differences, "changes": changes, "text_changes": text,
            "improved": sum(c["change"] == "improved" for c in changes), "regressed": sum(c["change"] == "regressed" for c in changes)}


@router.get("/compare/{a_id}/{b_id}")
async def compare_analyses(a_id: str, b_id: str):
    return compare(_get(a_id), _get(b_id))


def _finding(a: dict, finding_id: str) -> dict:
    f = next((f for f in a["findings"] if f["id"] == finding_id), None)
    if f is None:
        raise HTTPException(status_code=404, detail="finding not found")
    return f


def _document_text(a: dict) -> str:
    from app.api.policies import find_policy
    d = a.get("document")
    doc = find_policy(d["id"], d["version"]) if d else None
    if doc is None:
        raise HTTPException(status_code=422, detail="only a saved policy (uploaded or pasted) can be edited; reference policies cannot")
    return doc["text"]


@router.post("/{analysis_id}/findings/{finding_id}/redline")
async def propose_redline(analysis_id: str, finding_id: str):
    """Proposed wording for one finding, anchored to the exact characters of the audited document version."""
    import asyncio
    from app.compass import redline, workflow
    a = _get(analysis_id)
    f = _finding(a, finding_id)
    text = _document_text(a)
    proposal = await asyncio.to_thread(redline.propose, f, text, workflow.get_llm())
    return {**proposal, "finding_id": finding_id, "document": a["document"]}


class RedlineBody(BaseModel):
    mode: str
    span: list[int]
    original: str = ""
    proposed: str
    obligation_id: str | None = None


@router.post("/{analysis_id}/findings/{finding_id}/redline/accept")
async def accept_redline(analysis_id: str, finding_id: str, body: RedlineBody, request: Request):
    """Apply the (possibly edited) wording as a new version of the document, re-audit it on the same terms, and compare."""
    from app.api.policies import DOCUMENTS
    from app.compass import redline
    a = _get(analysis_id)
    f = _finding(a, finding_id)
    d = a["document"] or {}
    if not d or DOCUMENTS.get(d["id"]) is None:
        raise HTTPException(status_code=422, detail="only a saved policy can be edited")
    if DOCUMENTS.get(d["id"])["version"] != d["version"]:
        raise HTTPException(status_code=409, detail="the policy has a newer version than this audit; audit the latest version first")
    if not body.proposed.strip() or len(body.proposed) > 4000:
        raise HTTPException(status_code=422, detail="the proposed wording is empty or too long")
    try:
        new_text = redline.apply(_document_text(a), body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    version = DOCUMENTS.add_version(d["id"], new_text, f"Redline for {f['obligation_title']}")
    user = getattr(request.state, "user", None) or {}
    ANALYSES.review(analysis_id, len(ANALYSES.events(analysis_id)), {"finding_id": finding_id, "decision": "redline_accepted",
                    "note": f"version {version['n']}", "user_id": user.get("id"), "user_name": user.get("name") or user.get("email")})
    applicability = (a.get("applicability") or {}).get("answers")
    new = await analyze(AnalyzeBody(policy_id=d["id"], version=version["n"], policy_name=a["policy_name"],
                                    as_of=date.fromisoformat(a["assessed_on"]) if a.get("assessed_on") else None, applicability=applicability))
    return {"analysis": new, "comparison": compare(_get(analysis_id), new)}


@router.post("/{analysis_id}/findings/{finding_id}/redline/reject")
async def reject_redline(analysis_id: str, finding_id: str, request: Request):
    a = _get(analysis_id)
    _finding(a, finding_id)
    user = getattr(request.state, "user", None) or {}
    ANALYSES.review(analysis_id, len(ANALYSES.events(analysis_id)), {"finding_id": finding_id, "decision": "redline_rejected",
                    "user_id": user.get("id"), "user_name": user.get("name") or user.get("email")})
    return _get(analysis_id)


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str):
    return _get(analysis_id)

@router.get("/{analysis_id}/findings")
async def get_findings(analysis_id: str):
    return _get(analysis_id)["findings"]

@router.get("/{analysis_id}/metrics")
async def get_metrics(analysis_id: str):
    return run_all(_get(analysis_id))
