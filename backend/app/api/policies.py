"""Policy documents: owner-scoped, versioned and persisted. Each upload, paste or accepted edit is a version with its
text and sha256, so an audit can name exactly what it read and two versions can be compared."""
from __future__ import annotations

import hashlib
import json
import re
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.compliance import current_uid
from app.api.uploads import read_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/policies", tags=["policies"])


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentStore:
    """documents (one per policy) and versions (its texts). Every read and write is scoped to current_uid;
    with no user (auth disabled, or the service API key) nothing is filtered, as for analyses.
    ponytail: single-file SQLite with one lock; move to Postgres with the analyses."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, owner TEXT, name TEXT NOT NULL, company TEXT,
                created_at TEXT NOT NULL, source TEXT NOT NULL, meta TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS versions (doc_id TEXT NOT NULL, n INTEGER NOT NULL, text TEXT NOT NULL,
                sha256 TEXT NOT NULL, created_at TEXT NOT NULL, note TEXT, PRIMARY KEY (doc_id, n));
            CREATE INDEX IF NOT EXISTS documents_owner ON documents(owner);""")

    def create(self, name: str, text: str, source: str, company: str | None = None, meta: dict | None = None, note: str | None = None) -> dict:
        did = f"pol_{uuid.uuid4().hex[:10]}"
        with self._lock:
            self._db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)", (did, current_uid.get(), name, company, _now(), source, json.dumps(meta or {})))
            self._db.execute("INSERT INTO versions VALUES (?, 1, ?, ?, ?, ?)", (did, text, sha256(text), _now(), note or source))
            self._db.commit()
        return self.get(did)

    def add_version(self, did: str, text: str, note: str | None = None) -> dict:
        """A new version, unless the text equals the latest one (then the latest is returned)."""
        doc = self.get(did)
        if doc is None:
            raise KeyError(did)
        latest = doc["versions"][-1]
        if latest["sha256"] == sha256(text):
            return latest
        with self._lock:
            self._db.execute("INSERT INTO versions VALUES (?, ?, ?, ?, ?, ?)", (did, latest["n"] + 1, text, sha256(text), _now(), note))
            self._db.commit()
        return self.get(did)["versions"][-1]

    def find_by_text(self, text: str) -> dict | None:
        """The caller's most recent document whose latest version is exactly this text."""
        uid = current_uid.get()
        row = self._db.execute("""SELECT d.id FROM documents d JOIN versions v ON v.doc_id = d.id
            WHERE (? IS NULL OR d.owner = ?) AND v.sha256 = ? AND v.n = (SELECT MAX(n) FROM versions WHERE doc_id = d.id)
            ORDER BY d.created_at DESC LIMIT 1""", (uid, uid, sha256(text))).fetchone()
        return self.get(row[0]) if row else None

    def get(self, did: str) -> dict | None:
        uid = current_uid.get()
        row = self._db.execute("SELECT id, name, company, created_at, source, meta FROM documents WHERE id = ? AND (? IS NULL OR owner = ?)",
                               (did, uid, uid)).fetchone()
        if not row:
            return None
        versions = [{"n": n, "sha256": h, "created_at": c, "note": note, "chars": size} for n, h, c, note, size in self._db.execute(
            "SELECT n, sha256, created_at, note, LENGTH(text) FROM versions WHERE doc_id = ? ORDER BY n", (did,))]
        return {**json.loads(row[5]), "id": row[0], "name": row[1], "company": row[2], "uploaded_at": row[3], "source": row[4],
                "status": "READY", "versions": versions, "version": versions[-1]["n"]}

    def text(self, did: str, n: int | None = None) -> str | None:
        if self.get(did) is None:
            return None
        row = self._db.execute("SELECT text FROM versions WHERE doc_id = ? AND (? IS NULL OR n = ?) ORDER BY n DESC LIMIT 1", (did, n, n)).fetchone()
        return row[0] if row else None

    def list(self) -> list[dict]:
        uid = current_uid.get()
        ids = [r[0] for r in self._db.execute("SELECT id FROM documents WHERE (? IS NULL OR owner = ?) ORDER BY created_at DESC", (uid, uid))]
        return [self.get(i) for i in ids]

    def delete(self, did: str) -> bool:
        if self.get(did) is None:
            return False
        with self._lock:
            self._db.execute("DELETE FROM versions WHERE doc_id = ?", (did,))
            self._db.execute("DELETE FROM documents WHERE id = ?", (did,))
            self._db.commit()
        return True

    def delete_user(self, uid: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM versions WHERE doc_id IN (SELECT id FROM documents WHERE owner = ?)", (uid,))
            self._db.execute("DELETE FROM documents WHERE owner = ?", (uid,))
            self._db.commit()


DOCUMENTS = DocumentStore(Path(os.getenv("DOCUMENTS_DB") or Path(__file__).resolve().parents[2] / "storage" / "documents.db"))


def find_policy(policy_id: str, version: int | None = None) -> dict | None:
    """The caller's policy with the text of one version (latest by default)."""
    doc = DOCUMENTS.get(policy_id)
    text = DOCUMENTS.text(policy_id, version) if doc else None
    if text is None:
        return None
    v = next(x for x in doc["versions"] if x["n"] == (version or doc["version"]))
    return {**doc, "text": text, "version": v["n"], "sha256": v["sha256"]}


@router.get("")
async def list_policies():
    return DOCUMENTS.list()


@router.get("/{policy_id}")
async def get_policy(policy_id: str):
    p = DOCUMENTS.get(policy_id)
    if p is None:
        raise HTTPException(status_code=404, detail="policy not found")
    return p


@router.get("/{policy_id}/versions/{n}")
async def get_version(policy_id: str, n: int):
    p = find_policy(policy_id, n)
    if p is None:
        raise HTTPException(status_code=404, detail="version not found")
    return {"id": policy_id, "name": p["name"], "n": p["version"], "sha256": p["sha256"], "text": p["text"]}


@router.get("/{policy_id}/compare/{a}/{b}")
async def compare_versions(policy_id: str, a: int, b: int):
    """Sentence-level changes between two versions of the caller's policy."""
    from app.compass.redline import diff
    ta, tb = DOCUMENTS.text(policy_id, a), DOCUMENTS.text(policy_id, b)
    if ta is None or tb is None:
        raise HTTPException(status_code=404, detail="version not found")
    return {"id": policy_id, "a": a, "b": b, "changes": diff(ta, tb)}


class NewVersion(BaseModel):
    text: str = Field(min_length=50, max_length=500_000)
    note: str | None = Field(default=None, max_length=300)


@router.post("/{policy_id}/versions")
async def add_version(policy_id: str, body: NewVersion):
    if DOCUMENTS.get(policy_id) is None:
        raise HTTPException(status_code=404, detail="policy not found")
    return DOCUMENTS.add_version(policy_id, body.text, body.note)


@router.delete("/{policy_id}")
async def delete_policy(policy_id: str):
    if not DOCUMENTS.delete(policy_id):
        raise HTTPException(status_code=404, detail="policy not found")
    return {"deleted": policy_id}


@router.post("/upload")
async def upload_policy(file: UploadFile = File(...), company_id: str | None = None):
    content = await read_upload(file)
    name = file.filename or "policy.txt"
    try:
        from app.ingestion.parsers import parse_document
        text = parse_document(content, name, document_id=name).raw_text
    except Exception as e:
        logger.warning("upload text extraction failed %s", e)
        raise HTTPException(status_code=422, detail="could not read text from this file")
    if not (text or "").strip():
        raise HTTPException(status_code=422, detail="no text found in this file")
    # A private upload stays in its owner's workspace; it is not added to the shared reference knowledge base.
    doc = DOCUMENTS.create(name, text, "upload", company_id, {"size": len(content)})
    logger.info("upload %s v1 chars=%d", doc["id"], len(text))
    return doc


class GenerateRequest(BaseModel):
    company: str | None = None
    address: str | None = None
    website: str | None = None
    service: str | None = None
    sector: str | None = None
    data: str | None = None
    data_auto: str | None = None
    purpose: str | None = None
    consent_method: str | None = None
    languages: str | None = None
    withdraw_method: str | None = None
    sharing: str | None = None
    storage_location: str | None = None
    security: str | None = None
    children: str | None = None
    retention: str | None = None
    dpo_name: str | None = None
    contact: str | None = None
    grievance_days: str | None = None
    rights_channel: str | None = None
    proceed: bool = False  # draft now, leaving [placeholders] for anything the intake review asked about


PLACEHOLDERS = {"company": "[company legal name]", "data": "[list each item of personal data you collect]",
                "purpose": "[each specific purpose]", "sharing": "[categories of recipients, or 'not shared']",
                "retention": "[retention period for each kind of data, and the law that requires it]",
                "children": "[whether anyone under 18 can use the service, and how parental consent is verified]",
                "contact": "[grievance officer / DPO email and phone]", "dpo_name": "[name or designation of the DPO]",
                "grievance_days": "[N, at most 90]", "security": "[the safeguards you use, e.g. encryption, access control]",
                "consent_method": "[how a person gives consent, e.g. ticking an unticked box]",
                "withdraw_method": "[where a person withdraws consent, e.g. Settings > Privacy]", "rights_channel": "[email or form for requests]",
                "website": "[link to your website or app privacy page]", "service": "[one sentence on what your service does]"}
OPTIONAL = ("address", "data_auto", "languages", "storage_location", "rights_channel")


@router.post("/generate")
async def generate_policy(req: GenerateRequest):
    """Draft from the rule book, so the draft passes the same rules the audit applies. An AI rewrite is kept only if it still does."""
    from app.compass import rulebook
    from app.compass.audit import judge_rules
    from app.compass.intake import review
    intake = review(req.model_dump())
    if not intake["complete"] and not req.proceed:
        return {"needs_more": True, "message": intake["message"], "questions": intake["questions"],
                "recommendations": intake["recommendations"], "missing_fields": sorted({q["field"] for q in intake["questions"]}), "draft": None}
    asked = {q["field"] for q in intake["questions"]}
    facts = {}
    for k in PLACEHOLDERS.keys() | set(OPTIONAL):
        given = (getattr(req, k) or "").strip()
        facts[k] = PLACEHOLDERS[k] if k in asked or (not given and k not in OPTIONAL) else given
    sector = req.sector or "Technology"
    draft = rulebook.draft(facts)

    def passes(text: str) -> bool:
        return all(r["met"] for r in rulebook.check(text).values()) and all(v["status"] == "Satisfied" for v in judge_rules(text).values())

    llm_refined = False
    from app.config import settings
    if not settings.mock_llm and (settings.llm_api_key or settings.openai_api_key) and passes(draft):
        try:
            from app.services.llm import get_llm
            from app.agents.policy_generation_agent import SYSTEM_POLICY_GEN
            prompt = (f"Base draft:\n{draft}\n\nPolish the wording for a {sector} company. Keep every section, heading, fact, number, "
                      "email address and legal commitment exactly; do not add [placeholders]. Return only the final Markdown policy.")
            refined = (await get_llm().complete(prompt, system=SYSTEM_POLICY_GEN) or "").strip()
            if passes(refined):  # a rewrite that breaks any rule-book requirement is discarded
                draft, llm_refined = refined, True
        except Exception as e:
            logger.warning("policy generate LLM refinement skipped: %s", e)

    book = rulebook.check(draft)
    # Saved like any other policy, so it survives reloads, shows on the dashboard and can be audited by id.
    doc = DOCUMENTS.create(f"Generated policy — {facts['company']}"[:200], draft, "generated", facts["company"], {"sector": sector})
    return {
        "policy_id": doc["id"],
        "draft": draft,
        "llm_refined": llm_refined,
        "company": facts["company"],
        "sector": sector,
        "obligations_covered": sum(r["met"] for r in book.values()),
        "dpdp_sections_cited": ["Section 5", "Section 6(1)", "Section 6(3)", "Section 6(4)", "Section 8(2)", "Section 8(3)", "Section 8(5)", "Section 8(6)",
                                "Section 8(7)", "Section 8(9)", "Section 8(10)", "Section 9", "Section 11", "Section 12", "Section 13", "Section 14"],
        "reference_benchmarks_used": False,
        "recommendations": intake["recommendations"],
        "placeholders": sorted(set(rulebook.PLACEHOLDER.findall(draft))),
        "drafted_with_gaps": sorted(asked),
        "rulebook": [{"id": k, "met": r["met"], "fixes": [c["fix"] for c in r["checks"] if not c["passed"]]} for k, r in book.items()],
    }
