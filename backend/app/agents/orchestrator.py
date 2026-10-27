import logging
import time
from typing import Literal
from app.models.schemas import AgentStep
from app.config import settings

logger = logging.getLogger(__name__)


async def orchestrate(
    query: str,
    mode: Literal["business", "citizen"],
    policy_text: str | None = None,
    policy_id: str | None = None,
    defer_answer: bool = False,
) -> dict:
    try:
        from app.graph.workflow import run_workflow
        _t = time.perf_counter()
        result = await run_workflow(query=query, mode=mode, company_id=policy_id, policy_text=policy_text, defer_answer=defer_answer)
        logger.info("orchestrate timing workflow_ms=%d", (time.perf_counter() - _t) * 1000)
        findings = result.get("findings", [])
        risks = result.get("risks", [])
        obligations = result.get("obligations", [])
        trace = result.get("trace", [])
        guard = result.get("guardrail_results", [])
        legal_ev = result.get("evidence_legal", [])
        policy_ev = result.get("evidence_policy", [])
        citations = []
        for f in findings:
            for ev in list(f.get("legal_evidence", [])) + list(f.get("policy_evidence", [])):
                if isinstance(ev, dict):
                    cit = ev.get("citation")
                    if cit:
                        citations.append(cit)
                elif hasattr(ev, "citation"):
                    citations.append(ev.citation)
        from app.config import settings as _s
        from app.services.llm import get_llm
        _llm = get_llm()
        model_used = getattr(_llm, "model_used", getattr(_llm, "model", "mock"))
        from app.retrieval.hybrid_retriever import last_retrieval_diag
        legal_count = len(result.get("evidence_legal", []))
        evidence_status = "SUFFICIENT" if legal_count >= 2 else ("PARTIAL" if legal_count >= 1 else "INSUFFICIENT_EVIDENCE")
        return {
            "mode": mode,
            "intent": f"{'citizen_qa' if mode == 'citizen' else 'business_audit'}",
            "status": result.get("status", "COMPLETED"),
            "evidence_status": evidence_status,
            "detected_language": result.get("detected_language", "en"),
            "obligations": obligations,
            "findings": findings,
            "risks": risks,
            "citations": citations,
            "trace": trace,
            "guardrails": guard,
            "evidence": {"legal": legal_ev, "policy": policy_ev},
            "iterations": result.get("iterations", 0),
            "duration_ms": sum(s.get("duration_ms", 0) for s in trace),
            "model_used": model_used,
            "provider": "openrouter" if "openrouter" in (_s.llm_base_url or "") else "mock",
            "embedding_model": _s.embedding_model,
            "retrieval": last_retrieval_diag(),
            "top_k": _s.top_k,
            "final_answer": result.get("final_answer"),
        }
    except Exception as e:
        logger.error("orchestrate failed: %s", e)
        from app.agents.graph import run_analysis
        state = await run_analysis(policy_id or "unknown", query)
        return {
            "mode": mode, "status": "COMPLETED",
            "findings": state.get("findings", []),
            "risks": state.get("risks", []),
            "trace": state.get("trace", []),
            "guardrails": state.get("guardrail_results", []),
            "evidence": {"legal": state.get("retrieved_legal", []), "policy": state.get("retrieved_policy", [])},
        }
