"""Figure 3 Multi-Agent Workflow (Online) + System Arch 3.x — 5 agents with feedback loop
3.1 Orchestrator → 3.2 Retrieval (hybrid) → 3.3 Obligation Mapping → 3.4 Compliance Checking → 3.5 Risk Assessment → Final
Now delegates to real agents (retrieval_agent, obligation_mapping_agent, etc.) with bounded feedback loop in orchestrator.
Kept as LangGraph for observability; mock fallback when LLM not configured.
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
import time
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    policy_id: str
    query: str
    retrieved_legal: list
    retrieved_policy: list
    obligations: list
    findings: list
    guardrail_results: list
    trace: list
    mode: str  # business | citizen
    iterations: int

# Real agent nodes — each logs and returns citations
async def orchestrator_node(state: AgentState):
    # Understand intent — Business vs Citizen (query contains citizen QA?)
    q = state.get("query","")
    # Heuristic: if query is question-like and no policy_id meaningful → citizen
    mode = "citizen" if (q and "?" in q) and not state.get("policy_id","").startswith("pol_") else "business"
    # Allow explicit mode override
    mode = state.get("mode", mode)
    state["mode"] = mode  # type: ignore
    state["trace"].append({"agent":"Orchestrator","status":"COMPLETED","duration_ms": 20, "output_summary": f"Mode={mode} intent={'QA' if mode=='citizen' else 'audit'}"})
    return state

async def retrieval_node(state: AgentState):
    from app.agents.retrieval_agent import retrieve_evidence, has_sufficient_evidence
    t0=time.time()
    q = state.get("query","DPDP obligations")
    # Hybrid — legal + policy
    legal = await retrieve_evidence(q, mode="legal")
    # For citizen, policy retrieval = same query (company policy)
    # For business, use policy_id text if present else query
    policy_q = state.get("query","")
    policy = await retrieve_evidence(policy_q, mode="policy") if policy_q else []
    state["retrieved_legal"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in legal]  # type: ignore
    state["retrieved_policy"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in policy]  # type: ignore
    ms=int((time.time()-t0)*1000)
    state["trace"].append({"agent":"Retrieval","status":"COMPLETED","duration_ms": ms, "output_summary": f"Hybrid {len(legal)} legal + {len(policy)} policy"})
    # Insufficient → orchestrator loop handled in graph condition below
    state["_has_sufficient"] = has_sufficient_evidence(legal)  # type: ignore
    return state

async def obligation_mapping_node(state: AgentState):
    from app.agents.obligation_mapping_agent import map_obligations
    from app.models.schemas import RetrievedEvidence
    t0=time.time()
    legal_raw = state.get("retrieved_legal",[])
    # Convert dicts to RetrievedEvidence
    legal = [RetrievedEvidence(**e) if isinstance(e, dict) else e for e in legal_raw]  # type: ignore
    obligations = await map_obligations(legal, company_context=state.get("query",""))
    state["obligations"] = [o.model_dump() if hasattr(o,"model_dump") else o for o in obligations]  # type: ignore
    state["trace"].append({"agent":"Obligation Mapping","status":"COMPLETED","duration_ms": int((time.time()-t0)*1000), "output_summary": f"Mapped {len(obligations)}"})
    return state

async def compliance_checking_node(state: AgentState):
    from app.agents.compliance_agent import check_compliance
    from app.models.schemas import RetrievedEvidence, Obligation
    t0=time.time()
    legal = [RetrievedEvidence(**e) if isinstance(e, dict) else e for e in state.get("retrieved_legal",[])]  # type: ignore
    policy = [RetrievedEvidence(**e) if isinstance(e, dict) else e for e in state.get("retrieved_policy",[])]  # type: ignore
    obligations = [Obligation(**o) if isinstance(o, dict) else o for o in state.get("obligations",[])]  # type: ignore
    findings = await check_compliance(obligations, policy, legal)
    state["findings"] = [f.model_dump() if hasattr(f,"model_dump") else f for f in findings]  # type: ignore
    state["trace"].append({"agent":"Compliance Checking","status":"COMPLETED","duration_ms": int((time.time()-t0)*1000), "output_summary": f"Classified {len(findings)}"})
    return state

async def risk_reporting_node(state: AgentState):
    from app.agents.risk_agent import assess_risks
    from app.models.schemas import ComplianceFinding
    t0=time.time()
    findings = [ComplianceFinding(**f) if isinstance(f, dict) else f for f in state.get("findings",[])]  # type: ignore
    risks = await assess_risks(findings)
    state["_risks"] = [r.model_dump() if hasattr(r,"model_dump") else r for r in risks]  # type: ignore
    state["trace"].append({"agent":"Risk & Reporting","status":"COMPLETED","duration_ms": int((time.time()-t0)*1000), "output_summary": f"Risks {len(risks)}"})
    return state

async def guardrail_node(state: AgentState):
    from app.guardrails.engine import run_guardrails
    t0=time.time()
    findings = state.get("findings",[])
    guard = run_guardrails(findings)
    # Validate confidence + citation + prompt injection
    for f in findings:
        # Prompt injection check — retrieved docs treated as DATA
        for ev in list(f.get("legal_evidence",[])) + list(f.get("policy_evidence",[])):
            txt = (ev.get("excerpt") or ev.get("text") or "")[:500].lower()
            if "ignore previous instructions" in txt or "system:" in txt:
                guard.append({"id": f"gr_inject_{f.get('id')}", "rule": "Prompt injection in retrieved doc", "passed": False, "severity": "HIGH", "reason": "Retrieved excerpt contains imperative instruction — treated as DATA only"})
    state["guardrail_results"] = guard  # type: ignore
    state["trace"].append({"agent":"Guardrails","status":"COMPLETED","duration_ms": int((time.time()-t0)*1000), "output_summary": f"{sum(1 for g in guard if g['passed'])}/{len(guard)} passed"})
    return state

def should_retrieve_again(state: AgentState) -> str:
    # Feedback loop: if retrieval insufficient and iterations < max
    it = state.get("iterations",0)  # type: ignore
    has = state.get("_has_sufficient", True)  # type: ignore
    if not has and it < settings.max_feedback_iterations:
        state["iterations"] = it+1  # type: ignore
        logger.info("graph feedback retrieval %d", it+1)
        return "retrieval"
    return "obligation_mapping"

def should_recheck_compliance(state: AgentState) -> str:
    findings = state.get("findings",[])
    missing = sum(1 for f in findings if f.get("status")=="MISSING")
    it = state.get("iterations",0)  # type: ignore
    if missing >=2 and it < settings.max_feedback_iterations:
        # Could re-retrieve policy evidence
        logger.info("graph feedback compliance %d missing=%d", it, missing)
        return "retrieval"
    return "risk_reporting"

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("retrieval", retrieval_node)
    g.add_node("obligation_mapping", obligation_mapping_node)
    g.add_node("compliance_checking", compliance_checking_node)
    g.add_node("risk_reporting", risk_reporting_node)
    g.add_node("guardrails", guardrail_node)
    g.set_entry_point("orchestrator")
    g.add_edge("orchestrator", "retrieval")
    # Conditional feedback
    g.add_conditional_edges("retrieval", should_retrieve_again, {"retrieval": "retrieval", "obligation_mapping": "obligation_mapping"})
    g.add_edge("obligation_mapping", "compliance_checking")
    g.add_conditional_edges("compliance_checking", should_recheck_compliance, {"retrieval": "retrieval", "risk_reporting": "risk_reporting"})
    g.add_edge("risk_reporting", "guardrails")
    g.add_edge("guardrails", END)
    return g.compile()

graph = build_graph()

async def run_analysis(policy_id: str, policy_text: str = "", mode: str = "business") -> AgentState:
    initial: AgentState = {"policy_id": policy_id, "query": policy_text, "retrieved_legal": [], "retrieved_policy": [], "obligations": [], "findings": [], "guardrail_results": [], "trace": [], "mode": mode, "iterations": 0}  # type: ignore
    result = await graph.ainvoke(initial)
    return result

# Keep orchestrator-direct path also available for citizen
async def run_orchestrator(query: str, mode: str, policy_text: str | None = None) -> dict:
    from app.agents.orchestrator import orchestrate
    return await orchestrate(query=query, mode=mode, policy_text=policy_text, policy_id="citizen")
