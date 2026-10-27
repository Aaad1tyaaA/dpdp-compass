from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from enum import Enum

class ComplianceStatus(str, Enum):
    SATISFIED = "SATISFIED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class Urgency(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    SHORT_TERM = "SHORT_TERM"
    MEDIUM_TERM = "MEDIUM_TERM"
    LOW = "LOW"

class Citation(BaseModel):
    id: str
    source_document: str
    section: Optional[str] = None
    clause: Optional[str] = None
    page: Optional[int] = None
    text: str
    type: Literal["LEGAL","POLICY"]

class Evidence(BaseModel):
    citation: Citation
    excerpt: str
    relevance_score: float = Field(ge=0, le=1)

class ComplianceFinding(BaseModel):
    id: str
    obligation_id: str
    obligation_title: str
    obligation_description: str
    principle: str
    status: ComplianceStatus
    severity: Severity
    urgency: Urgency
    reasoning: str
    policy_evidence: list[Evidence]
    legal_evidence: list[Evidence]
    confidence: float = Field(ge=0, le=1)
    recommended_action: str
    suggested_rewrite: Optional[str] = None

class AgentStep(BaseModel):
    agent: str
    status: Literal["PENDING","RUNNING","COMPLETED","FAILED"]
    duration_ms: Optional[int] = None
    output_summary: Optional[str] = None

class GuardrailResult(BaseModel):
    id: str
    rule: str
    passed: bool
    severity: Severity
    reason: str
    violated_rule: Optional[str] = None
    recommendation: Optional[str] = None

class Analysis(BaseModel):
    id: str
    policy_id: str
    policy_name: str
    created_at: datetime
    status: Literal["PROCESSING","COMPLETED","FAILED"]
    overall_score: int
    findings: list[ComplianceFinding]
    severity_counts: dict[str,int]
    status_counts: dict[str,int]
    agent_trace: list[AgentStep]
    guardrail_results: list[GuardrailResult]

class PolicyOut(BaseModel):
    id: str
    name: str
    company: Optional[str] = None
    uploaded_at: datetime
    status: str

class EvaluationMetric(BaseModel):
    id: str
    name: str
    description: str
    category: Literal["base","ragas","citation","custom","guardrail"]
    direction: Literal["higher_better","lower_better"]
    value: float
    threshold: float
    confidence: Optional[float] = None
    methodology: Optional[str] = None
    dataset_version: Optional[str] = None
    evaluated_at: datetime

class CitizenAnalysis(BaseModel):
    id: str
    policy_name: str
    summary: str
    your_rights: list[dict]
    company_obligations: list[dict]
    data_collected: list[str]
    purpose: list[str]
    sharing: str
    retention: str
    shortfalls: list[dict]
    trust_score: int
    citations: list[Citation]

# Typed agent outputs — keep backward compat, add structured
class RetrievedEvidence(BaseModel):
    chunk_id: str | None = None
    text: str
    source_document: str | None = None
    section: Optional[str] = None
    clause: Optional[str] = None
    page: Optional[int] = None
    citation: Optional[str] = None
    score: float = 0
    type: Literal["vector","sparse","graph","metadata"] = "vector"
    metadata: dict | None = None

class Obligation(BaseModel):
    obligation: str
    obligation_id: str | None = None  # e.g., DPDP-8.5
    source: str = "DPDP Act"
    section: Optional[str] = None
    applies_to: str | None = None  # Entity
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    evidence: list[RetrievedEvidence] = Field(default_factory=list)
    principle: Optional[str] = None

class RiskAssessment(BaseModel):
    finding_id: str
    severity: Severity
    impact: str
    likelihood: Literal["HIGH","MEDIUM","LOW"] = "MEDIUM"
    rationale: str
    recommendation: str

class FinalComplianceReport(BaseModel):
    summary: str
    overall_score: int
    findings: list[ComplianceFinding]
    risks: list[RiskAssessment] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

class CitizenResponse(BaseModel):
    summary: str
    data_collected: list[str]
    purposes: list[str] = Field(alias="purpose")
    sharing: str
    retention: str
    your_rights: list[dict]
    company_obligations: list[dict]
    compliance_concerns: list[dict] = Field(default_factory=list)
    trust_score: int
    citations: list[Citation]

# Request bodies
class AnalyzeRequest(BaseModel):
    policy_id: str

class CitizenAnalyzeRequest(BaseModel):
    policy_id: Optional[str] = None
    url: Optional[str] = None
    text: Optional[str] = None
