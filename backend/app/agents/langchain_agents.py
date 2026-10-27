"""LangChain-style specialist agents for the DPDP multi-agent RAG workflow.

The codebase already has battle-tested specialist functions. These wrappers give
each specialist an explicit agent boundary, typed input/output, and traceable
runtime metadata so LangGraph can compose them cleanly without duplicating logic.
"""

from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field

from app.graph.state import AgentState
from app.models.schemas import ComplianceFinding, Obligation, RetrievedEvidence, RiskAssessment


class OrchestratorDecision(BaseModel):
    mode: Literal["business", "citizen"] = "business"
    intent: Literal["citizen_question", "company_compliance", "company_policy_generation", "company_policy_update"] = "company_compliance"
    detected_language: Literal["en", "hi", "mr"] = "en"
    route: Literal["citizen", "business", "policy_generation"] = "business"


class RetrievalOutput(BaseModel):
    legal: list[RetrievedEvidence] = Field(default_factory=list)
    policy: list[RetrievedEvidence] = Field(default_factory=list)
    sufficient: bool = False


class ObligationMappingOutput(BaseModel):
    obligations: list[Obligation] = Field(default_factory=list)


class ComplianceOutput(BaseModel):
    findings: list[ComplianceFinding] = Field(default_factory=list)


class RiskReportingOutput(BaseModel):
    risks: list[RiskAssessment] = Field(default_factory=list)


class PolicyGenerationOutput(BaseModel):
    answer: str = ""


def _detect_language(query: str) -> Literal["en", "hi", "mr"]:
    devanagari = sum(1 for c in query if "\u0900" <= c <= "\u097F")
    if devanagari / max(len(query), 1) > 0.3:
        # Marathi and Hindi share Devanagari; use common Marathi markers first.
        if any(word in query for word in ["आहे", "माझा", "माझी", "काय", "करू"]):
            return "mr"
        return "hi"
    return "en"


def _classify_intent(query: str, mode: str | None) -> OrchestratorDecision:
    q = query.lower()
    detected = _detect_language(query)
    if mode == "citizen":
        return OrchestratorDecision(mode="citizen", intent="citizen_question", detected_language=detected, route="citizen")
    if any(kw in q for kw in ["create", "generate", "build", "draft", "write", "new policy"]):
        return OrchestratorDecision(mode="business", intent="company_policy_generation", detected_language=detected, route="policy_generation")
    if any(kw in q for kw in ["update", "improve", "revise", "fix", "rewrite", "change"]):
        return OrchestratorDecision(mode="business", intent="company_policy_update", detected_language=detected, route="policy_generation")
    return OrchestratorDecision(mode="business", intent="company_compliance", detected_language=detected, route="business")


def _as_evidence(items: list) -> list[RetrievedEvidence]:
    return [RetrievedEvidence(**e) if isinstance(e, dict) else e for e in items]


def _as_obligations(items: list) -> list[Obligation]:
    return [Obligation(**o) if isinstance(o, dict) else o for o in items]


def _as_findings(items: list) -> list[ComplianceFinding]:
    return [ComplianceFinding(**f) if isinstance(f, dict) else f for f in items]


class LangChainOrchestratorAgent:
    name = "Orchestrator"

    async def ainvoke(self, state: AgentState) -> OrchestratorDecision:
        return _classify_intent(state.get("query", ""), state.get("mode"))


async def _english_for_search(query: str) -> str:
    """The legal index is English-only; translate Hindi/Marathi questions for retrieval.
    The answer is still written in the user's language (detected_language is untouched)."""
    from app.config import settings
    from app.services.llm import get_llm
    if settings.mock_llm:
        return query
    try:
        out = await get_llm().complete(
            f"Translate this question into English. Reply with the translation only.\n\n{query[:500]}",
            system="You are a translator.",
        )
        return (out or "").strip().strip('"') or query
    except Exception:
        return query


class LangChainRetrievalAgent:
    name = "Retrieval"

    async def ainvoke(self, state: AgentState) -> RetrievalOutput:
        from app.agents.retrieval_agent import has_sufficient_evidence, retrieve_evidence

        query = state.get("query", "DPDP obligations")
        prior_legal = _as_evidence(state.get("evidence_legal", []))
        if state.get("retrieval_attempts", 0):
            # Feedback loop: reformulate instead of repeating the identical query.
            gaps = [f.get("obligation_title", "") for f in state.get("findings", []) if f.get("status") == "MISSING"]
            query = ("DPDP Act " + "; ".join(gaps[:4])) if gaps else f"DPDP Act 2023 Data Fiduciary obligations notice consent security breach rights {query[:200]}"
        elif state.get("detected_language", "en") != "en":
            query = await _english_for_search(query)
        legal = await retrieve_evidence(query, mode="legal")
        seen = {e.chunk_id or e.text[:80] for e in legal}
        legal += [e for e in prior_legal if (e.chunk_id or e.text[:80]) not in seen]

        policy: list[RetrievedEvidence] = []
        company_id = state.get("company_id")
        policy_text = state.get("policy_text") or ""
        if policy_text.strip():
            # Audit the text the user actually uploaded, not whatever the KB holds.
            from app.ingestion.clause_chunker import clause_aware_chunk
            chunks = clause_aware_chunk(policy_text, source_document="Uploaded policy", document_type="policy")
            policy = [RetrievedEvidence(chunk_id=f"upl_{i}", text=c.text[:1200], source_document="Uploaded policy",
                                        section=c.section, page=c.page_number, score=1.0) for i, c in enumerate(chunks)]
        elif company_id:
            policy = await retrieve_evidence(query, mode="policy", where={"company_id": company_id})
        elif state.get("mode") == "business":
            policy = await retrieve_evidence(query, mode="policy")
        return RetrievalOutput(legal=legal, policy=policy, sufficient=has_sufficient_evidence(legal))


class LangChainObligationMappingAgent:
    name = "Obligation Mapping"

    async def ainvoke(self, state: AgentState) -> ObligationMappingOutput:
        from app.agents.obligation_mapping_agent import map_obligations

        legal = _as_evidence(state.get("evidence_legal", []))
        obligations = await map_obligations(legal, company_context=state.get("query", ""), use_llm=state.get("mode") != "citizen")
        return ObligationMappingOutput(obligations=obligations)


class LangChainComplianceCheckingAgent:
    name = "Compliance Checking"

    async def ainvoke(self, state: AgentState) -> ComplianceOutput:
        from app.agents.compliance_agent import check_compliance

        legal = _as_evidence(state.get("evidence_legal", []))
        policy = _as_evidence(state.get("evidence_policy", []))
        obligations = _as_obligations(state.get("obligations", []))
        findings = await check_compliance(obligations, policy, legal, use_llm=state.get("mode") != "citizen")
        return ComplianceOutput(findings=findings)


class LangChainRiskReportingAgent:
    name = "Risk & Reporting"

    async def ainvoke(self, state: AgentState) -> RiskReportingOutput:
        from app.agents.risk_agent import assess_risks

        findings = _as_findings(state.get("findings", []))
        risks = await assess_risks(findings, use_llm=state.get("mode") != "citizen")
        return RiskReportingOutput(risks=risks)


class LangChainPolicyGenerationAgent:
    name = "Policy Generation/Rewrite"

    async def ainvoke(self, state: AgentState) -> PolicyGenerationOutput:
        from app.agents.policy_generation_agent import generate_citizen_answer, generate_policy_draft

        if state.get("mode") == "citizen":
            answer = await generate_citizen_answer(state)
        else:
            answer = await generate_policy_draft(state)
        return PolicyGenerationOutput(answer=answer)


def trace_step(agent: str, started: float, summary: str) -> dict:
    return {
        "agent": agent,
        "status": "COMPLETED",
        "duration_ms": int((time.time() - started) * 1000),
        "output_summary": summary,
    }


orchestrator_agent = LangChainOrchestratorAgent()
retrieval_agent = LangChainRetrievalAgent()
obligation_mapping_agent = LangChainObligationMappingAgent()
compliance_checking_agent = LangChainComplianceCheckingAgent()
risk_reporting_agent = LangChainRiskReportingAgent()
policy_generation_agent = LangChainPolicyGenerationAgent()
