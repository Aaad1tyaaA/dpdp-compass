import time
import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)


def _detect_language(query: str) -> str:
    devanagari = sum(1 for c in query if "\u0900" <= c <= "\u097F")
    total = max(len(query), 1)
    if devanagari / total > 0.3:
        return "hi"
    return "en"


def _classify_intent(query: str, mode: str | None) -> Literal["citizen_question", "company_compliance", "company_policy_generation", "company_policy_update"]:
    q = query.lower()
    if mode == "citizen":
        return "citizen_question"
    gen_kw = ["create", "generate", "build", "draft", "write", "help us create", "new policy"]
    if any(kw in q for kw in gen_kw):
        return "company_policy_generation"
    upd_kw = ["update", "improve", "revise", "fix", "change"]
    if any(kw in q for kw in upd_kw):
        return "company_policy_update"
    return "company_compliance"


async def orchestrator_node(state: AgentState) -> AgentState:
    from app.agents.langchain_agents import orchestrator_agent, trace_step

    t0 = time.time()
    decision = await orchestrator_agent.ainvoke(state)
    state["detected_language"] = decision.detected_language
    state["mode"] = decision.mode
    state.setdefault("trace", []).append(trace_step(
        "Orchestrator",
        t0,
        f"mode={decision.mode} intent={decision.intent} lang={decision.detected_language}",
    ))
    return state


async def retrieval_node(state: AgentState) -> AgentState:
    from app.agents.langchain_agents import retrieval_agent, trace_step

    t0 = time.time()
    result = await retrieval_agent.ainvoke(state)
    state["evidence_legal"] = [e.model_dump() for e in result.legal]
    state["evidence_policy"] = [e.model_dump() for e in result.policy]
    state["retrieval_attempts"] = state.get("retrieval_attempts", 0) + 1
    state["iterations"] = state.get("iterations", 0) + 1
    state.setdefault("trace", []).append(trace_step("Retrieval", t0, f"legal={len(result.legal)} policy={len(result.policy)} sufficient={result.sufficient}"))
    return state


async def obligation_mapping_node(state: AgentState) -> AgentState:
    from app.agents.langchain_agents import obligation_mapping_agent, trace_step

    t0 = time.time()
    result = await obligation_mapping_agent.ainvoke(state)
    state["obligations"] = [o.model_dump() for o in result.obligations]
    state.setdefault("trace", []).append(trace_step("Obligation Mapping", t0, f"mapped={len(result.obligations)}"))
    return state


async def compliance_checking_node(state: AgentState) -> AgentState:
    from app.agents.langchain_agents import compliance_checking_agent, trace_step

    t0 = time.time()
    result = await compliance_checking_agent.ainvoke(state)
    state["findings"] = [f.model_dump() for f in result.findings]
    state.setdefault("trace", []).append(trace_step("Compliance Checking", t0, f"classified={len(result.findings)}"))
    return state


async def risk_reporting_node(state: AgentState) -> AgentState:
    from app.agents.langchain_agents import risk_reporting_agent, trace_step

    t0 = time.time()
    result = await risk_reporting_agent.ainvoke(state)
    state["risks"] = [r.model_dump() for r in result.risks]
    state.setdefault("trace", []).append(trace_step("Risk & Reporting", t0, f"risks={len(result.risks)}"))
    return state


async def guardrail_node(state: AgentState) -> AgentState:
    from app.guardrails.engine import run_guardrails
    t0 = time.time()
    guard = run_guardrails(state.get("findings", []))
    state["guardrail_results"] = guard
    state.setdefault("trace", []).append({
        "agent": "Guardrails", "status": "COMPLETED",
        "duration_ms": int((time.time() - t0) * 1000),
        "output_summary": f"passed={sum(1 for g in guard if g.get('passed'))}/{len(guard)}",
    })
    state["status"] = "COMPLETED"
    return state


async def citizen_answer_node(state: AgentState) -> AgentState:
    from app.agents.langchain_agents import policy_generation_agent, trace_step

    t0 = time.time()
    if not state.get("guardrail_results"):
        # Quick path (no audit): still apply the evidence-first guardrails to what the answer is built on.
        from app.guardrails.engine import guardrail_prompt_injection
        legal = state.get("evidence_legal", [])
        state["guardrail_results"] = [{
            "id": "gr_citizen_evidence", "rule": "Answer grounded in legal evidence", "passed": bool(legal),
            "severity": "HIGH", "reason": f"{len(legal)} DPDP passages retrieved" if legal else "No legal evidence retrieved",
        }] + guardrail_prompt_injection([{"id": "citizen", "legal_evidence": [{"text": e.get("text", "")} for e in legal]}])
    if state.get("defer_answer"):
        # Streaming endpoint writes the answer itself, token by token, from this same state.
        state["final_answer"] = None
        state["status"] = "COMPLETED"
        state.setdefault("trace", []).append(trace_step("Citizen Answer", t0, "deferred to stream"))
        return state
    result = await policy_generation_agent.ainvoke(state)
    state["final_answer"] = result.answer
    state["status"] = "COMPLETED"
    state.setdefault("trace", []).append(trace_step("Citizen Answer", t0, f"answer_len={len(result.answer) if result.answer else 0}"))
    return state


async def policy_generation_node(state: AgentState) -> AgentState:
    from app.agents.langchain_agents import policy_generation_agent, trace_step

    t0 = time.time()
    result = await policy_generation_agent.ainvoke(state)
    state["final_answer"] = result.answer
    state["status"] = "COMPLETED"
    state.setdefault("trace", []).append(trace_step("Policy Generation", t0, f"draft_len={len(result.answer) if result.answer else 0}"))
    return state


def _should_retrieve_again(state: AgentState) -> str:
    it = state.get("iterations", 0)
    legal_ev = state.get("evidence_legal", [])
    if not legal_ev and it < settings.max_feedback_iterations:
        return "retrieval"
    return "obligation_mapping"


def _route_after_orchestrator(state: AgentState) -> str:
    return "retrieval"


def _route_after_retrieval(state: AgentState) -> str:
    nxt = _should_retrieve_again(state)
    # A citizen question with no company policy has nothing to audit: answer straight from the law
    # instead of running obligation mapping / compliance / risk (6-8 wasted LLM calls, ~2.5 min).
    if nxt == "obligation_mapping" and state.get("mode") == "citizen" and not state.get("policy_text"):
        return "citizen_answer"
    return nxt


def _route_after_compliance(state: AgentState) -> str:
    findings = state.get("findings", [])
    missing = sum(1 for f in findings if f.get("status") == "MISSING")
    it = state.get("iterations", 0)
    # With an uploaded policy, MISSING means the policy lacks it — more legal retrieval can't change that.
    if missing >= 2 and it < settings.max_feedback_iterations and not state.get("policy_text"):
        return "retrieval"
    return "risk_reporting"


def _route_after_guardrails(state: AgentState) -> str:
    mode = state.get("mode", "business")
    if mode == "business" and state.get("policy_text"):
        # An audit's "query" is the policy itself; words like "update" in it must not trigger drafting.
        return "END"
    intent = _classify_intent(state.get("query", ""), mode)
    if intent == "citizen_question":
        return "citizen_answer"
    if intent in ("company_policy_generation", "company_policy_update"):
        return "policy_generation"
    return "END"


def build_workflow():
    g = StateGraph(AgentState)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("retrieval", retrieval_node)
    g.add_node("obligation_mapping", obligation_mapping_node)
    g.add_node("compliance_checking", compliance_checking_node)
    g.add_node("risk_reporting", risk_reporting_node)
    g.add_node("guardrails", guardrail_node)
    g.add_node("citizen_answer", citizen_answer_node)
    g.add_node("policy_generation", policy_generation_node)
    g.set_entry_point("orchestrator")
    g.add_conditional_edges("orchestrator", _route_after_orchestrator, {"retrieval": "retrieval"})
    g.add_conditional_edges("retrieval", _route_after_retrieval, {
        "retrieval": "retrieval", "obligation_mapping": "obligation_mapping", "citizen_answer": "citizen_answer",
    })
    g.add_edge("obligation_mapping", "compliance_checking")
    g.add_conditional_edges("compliance_checking", _route_after_compliance, {
        "retrieval": "retrieval", "risk_reporting": "risk_reporting",
    })
    g.add_edge("risk_reporting", "guardrails")
    g.add_conditional_edges("guardrails", _route_after_guardrails, {
        "citizen_answer": "citizen_answer", "policy_generation": "policy_generation", "END": END,
    })
    g.add_edge("citizen_answer", END)
    g.add_edge("policy_generation", END)
    return g.compile()


workflow = build_workflow()


async def run_workflow(query: str, mode: str = "business", company_id: str | None = None,
                       document_id: str | None = None, policy_text: str | None = None,
                       defer_answer: bool = False) -> AgentState:
    initial: AgentState = {
        "query": query, "detected_language": "en", "mode": mode,
        "uploaded_document_id": document_id, "company_id": company_id, "policy_text": policy_text, "defer_answer": defer_answer,
        "decomposed_queries": [], "dpdp_documents": [], "company_documents": [],
        "graph_evidence": [], "extracted_clauses": [], "identified_data_practices": [],
        "legal_requirements": [], "compliance_findings": [], "retrieval_attempts": 0,
        "final_answer": None, "citations": [], "risks": [], "obligations": [],
        "findings": [], "guardrail_results": [], "trace": [],
        "iterations": 0, "evidence_legal": [], "evidence_policy": [], "status": "RUNNING",
    }
    result = await workflow.ainvoke(initial)
    return result
