from typing import TypedDict, Optional


class AgentState(TypedDict):
    query: str
    detected_language: str
    mode: str
    uploaded_document_id: Optional[str]
    company_id: Optional[str]
    policy_text: Optional[str]
    defer_answer: bool
    decomposed_queries: list[str]
    dpdp_documents: list
    company_documents: list
    graph_evidence: list
    extracted_clauses: list
    identified_data_practices: list
    legal_requirements: list
    compliance_findings: list
    retrieval_attempts: int
    final_answer: Optional[str]
    citations: list
    risks: list
    obligations: list
    findings: list
    guardrail_results: list
    trace: list
    iterations: int
    evidence_legal: list
    evidence_policy: list
    status: str
