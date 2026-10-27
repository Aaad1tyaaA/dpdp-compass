from fastapi import APIRouter, HTTPException
from app.evaluation.registry import run_all, REGISTRY
from app.api.compliance import ANALYSES

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


def _analysis(analysis_id: str) -> dict:
    a = ANALYSES.get(analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return a


@router.get("/registry/list")
async def list_registry():
    return [{"key":k, "name":v.definition.name, "category":v.definition.category, "threshold":v.definition.threshold} for k,v in REGISTRY.items()]

@router.get("/{analysis_id}")
async def get_evaluation(analysis_id: str):
    return {"analysis_id": analysis_id, "metrics": run_all(_analysis(analysis_id))}

@router.get("/{analysis_id}/metrics")
async def get_metrics(analysis_id: str):
    return run_all(_analysis(analysis_id))

@router.get("/{analysis_id}/guardrails")
async def get_guardrails(analysis_id: str):
    from app.guardrails.engine import run_guardrails
    return run_guardrails(_analysis(analysis_id).get("findings", []))
