"""Engine endpoints: grounded question answering, policy audit, and knowledge-base statistics."""
from __future__ import annotations

import asyncio

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.compass import adapter, sources, workflow

router = APIRouter(prefix="/api/compass", tags=["compass"])


class Ask(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class Audit(BaseModel):
    policy_text: str = Field(min_length=50, max_length=200_000)
    as_of: date | None = None  # assessment date for "in force" statuses; default today
    applicability: dict[str, str] | None = None


@router.get("/kb")
async def kb() -> dict:
    """Counts for the knowledge base built from the Act (chunks, obligations, graph)."""
    return await asyncio.to_thread(adapter.kb_stats)


@router.post("/ask")
async def ask(body: Ask) -> dict:
    """Answer a question from the Act. Every cited provision exists and was retrieved for the question."""
    return await asyncio.to_thread(workflow.run, body.question)


@router.post("/audit")
async def audit(body: Audit) -> dict:
    """Audit a privacy policy against the 14-obligation checklist."""
    return await asyncio.to_thread(workflow.run, "", body.policy_text, "auto", body.as_of, body.applicability)


@router.get("/applicability")
async def applicability_questions() -> list[dict]:
    """The questions that decide which obligations apply."""
    from app.compass.applicability import QUESTIONS
    return [{**q, "options": [{"value": k, "label": v} for k, v in q["options"].items()]} for q in QUESTIONS]


@router.get("/sources/{doc_id}/file")
async def legal_source_file(doc_id: str):
    """The official Gazette PDF itself (public documents), so a citation can open at its page."""
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    doc = next((d for d in sources.REGISTRY if d["id"] == doc_id), None)
    path = sources.LEGAL / doc["file"] if doc else None
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="source not found")
    return FileResponse(path, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{path.name}"'})


@router.get("/sources")
async def legal_sources(on: date | None = None) -> dict:
    """The official documents the engine uses, the corrigendum applied, and each obligation's commencement on a date."""
    from app.compass.checklist import CHECKLIST
    on = on or date.today()
    return {"assessed_on": on.isoformat(), "documents": await asyncio.to_thread(sources.registry),
            "obligations": [{"id": ob["id"], "title": ob["title"], **sources.status(ob["provision"], on)} for ob in CHECKLIST],
            "milestones": [{"date": d.isoformat(), "what": w} for d, w in (
                (sources.PUBLISHED, "Definitions, the Board (ss 18-26), rule-making and Rules 1, 2, 17-21"),
                (sources.ONE_YEAR, "Consent Managers: section 6(9), 27(1)(d) and Rule 4"),
                (sources.EIGHTEEN_MONTHS, "Data Fiduciary obligations, rights, penalties: ss 3-17, 27-34, 36, 37 and Rules 3, 5-16, 22, 23"))]}
