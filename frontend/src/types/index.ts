export type ComplianceStatus = "SATISFIED" | "PARTIAL" | "MISSING" | "NOT_APPLICABLE"
export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO"
export type Urgency = "IMMEDIATE" | "SHORT_TERM" | "MEDIUM_TERM" | "LOW"

export interface Citation {
  id: string
  source_document: string
  section?: string
  clause?: string
  page?: number
  text: string
  type: "LEGAL" | "POLICY"
  /** Character span of a policy quote in the audited document version. */
  span?: [number, number] | null
  /** Link to the official source (the Gazette PDF, at its page). */
  url?: string
}

export interface Evidence {
  citation: Citation
  excerpt: string
  relevance_score: number
}

export interface ComplianceFinding {
  id: string
  obligation_id: string
  obligation_title: string
  obligation_description: string
  principle: string
  status: ComplianceStatus
  severity: Severity
  urgency: Urgency
  reasoning: string
  policy_evidence: Evidence[]
  legal_evidence: Evidence[]
  confidence: number
  recommended_action: string
  /** Rule-book requirements this finding fails, each as a concrete fix. */
  fixes?: string[]
  /** Every rule-book requirement for this obligation, met or not, with its legal basis. */
  rule_checks?: { rule: string; passed: boolean; fix: string; basis: string }[]
  suggested_rewrite?: string
  /** Provisions of the Act that carve out exceptions to this obligation, e.g. "17(3)". */
  exemptions?: string[]
  /** Guardrail checks that changed or flagged this finding. */
  guardrail_flags?: string[]
  /** Commencement of the obligation (G.S.R. 843(E)) and its status on the assessment date. */
  in_force_from?: string | null
  legal_status?: "In force" | "Not yet in force" | "Unknown"
  assessed_on?: string
  /** The latest reviewer decision; null while the finding is automated only. */
  review?: { seq: number; decision: "accept" | "override"; status?: ComplianceStatus | null; note?: string | null; user_name?: string | null; at: string } | null
  /** How the verdict is backed: a verbatim quote, clauses that contradict each other, or nothing quoted. */
  support?: "quoted" | "conflicting" | "not quoted" | "absent"
  conflicts?: PolicyConflict[]
  /** Policy passages the audit read for this obligation, with their spans in the document. */
  passages?: { text: string; span: [number, number] | null }[]
  /** False when the applicability answers take this obligation out of scope; model_status keeps the model's verdict. */
  applies?: boolean
  model_status?: ComplianceStatus
  /** DPDP Rules, 2025 provisions that give the obligation its detail. */
  rules?: RuleRef[]
}

export interface RuleRef {
  page?: number | null
  url?: string
  provision: string
  label: string
  requirement: string
  in_force_from: string | null
  status: string
}

export interface Analysis {
  id: string
  policy_id: string
  policy_name: string
  created_at: string
  status: "PROCESSING" | "COMPLETED" | "FAILED"
  overall_score: number
  findings: ComplianceFinding[]
  severity_counts: Record<Severity, number>
  status_counts: Record<ComplianceStatus, number>
  agent_trace: AgentStep[]
  guardrail_results: GuardrailResult[]
  citations?: Citation[]
  risks?: RiskAssessment[]
  /** How the audit was judged. `degraded` is set when the language model was unavailable and keyword rules were used. */
  evidence?: { judge?: string; degraded?: string | null }
  /** Date the obligations were assessed against, and the official documents used. */
  assessed_on?: string
  sources?: { id: string; gazette: string; published: string }[]
  /** The saved policy version this audit read (absent for bundled reference policies). */
  /** Answers that decided which obligations apply, and notes (exemptions to verify, contradictions). */
  /** Reviewer decisions: optimistic-concurrency revision, newest-first trail, and the score with overrides applied. */
  review_rev?: number
  activity?: { seq: number; finding_id: string; decision: string; status?: string | null; note?: string | null; user_name?: string | null; at: string }[]
  reviewed_count?: number
  reviewed_score?: number | null
  conflicts?: PolicyConflict[]
  /** Requests for more input when the text looks incomplete. */
  input_notes?: string[]
  /** Text of a bundled reference policy (public), for the evidence viewer. */
  reference_text?: string | null
  applicability?: { answers: Record<string, string>; notes: string[] }
  /** Versioned scoring method shared by every view. */
  method?: { id: string; version: string; score: string; trust: string }
  document?: { id: string; name: string; version: number; sha256: string; source: string } | null
}

export interface RiskAssessment {
  finding_id: string
  severity: Severity
  impact: string
  likelihood: "HIGH" | "MEDIUM" | "LOW"
  rationale: string
  recommendation: string
}

export interface Policy {
  id: string
  name: string
  company?: string
  uploaded_at: string
  status: string
  url?: string
  /** Latest version number, and every version's hash and date (texts are fetched per version). */
  version?: number
  versions?: { n: number; sha256: string; created_at: string; note?: string | null; chars: number }[]
}

export interface AgentStep {
  agent: string
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"
  duration_ms?: number
  output_summary?: string
}

export interface GuardrailResult {
  id: string
  rule: string
  passed: boolean
  severity: Severity
  reason: string
  recommendation?: string
}

export interface EvaluationMetric {
  id: string
  name: string
  description: string
  category: "base" | "ragas" | "citation" | "custom" | "guardrail"
  direction: "higher_better" | "lower_better"
  value: number
  threshold: number
  confidence?: number
  methodology?: string
  dataset_version?: string
  evaluated_at: string
}

/** Sentence-level support of an answer by its sources (lexical heuristic, not a judgement of truth). */
export interface ClaimCheck {
  claims: { claim: string; status: "supported" | "uncertain" | "absent" | "contradicted"; reason: string; evidence: string }[]
  counts: Record<"supported" | "uncertain" | "absent" | "contradicted", number>
  method: string
}

export interface PolicyConflict {
  topic: string
  obligation_id: string
  a: { text: string; span: [number, number] }
  b: { text: string; span: [number, number] }
}

/** POST /api/compliance/{id}/findings/{fid}/redline */
export interface Redline {
  obligation_id: string
  mode: "replace" | "insert"
  span: [number, number]
  original: string
  proposed: string
  explanation: string
  placeholders: string[]
  source: string
}

/** GET /api/compliance/compare/{a}/{b}, and the result of accepting a redline. */
export interface AuditComparison {
  a: { id: string; version?: number; score: number }
  b: { id: string; version?: number; score: number }
  comparable: boolean
  differences: string[]
  changes: { obligation_id: string; title: string; from: string; to: string; change: "improved" | "regressed" | "scope" }[]
  text_changes: { op: "added" | "removed" | "modified"; a: string; b: string }[]
  improved: number
  regressed: number
}

export interface CitizenAnalysis {
  claim_check?: ClaimCheck
  id: string
  policy_name: string
  summary: string
  your_rights: { title: string; description: string; citation: Citation }[]
  company_obligations: { title: string; description: string }[]
  data_collected: string[]
  purpose: string[]
  sharing: string
  retention: string
  shortfalls: { title: string; severity: Severity; description: string }[]
  /** null when no company policy was analysed — a score without evidence would be fabricated. */
  trust_score: number | null
  policy_analyzed?: boolean
  citations: Citation[]
  guardrails?: { rule: string; passed: boolean; details?: string; reason?: string }[]
  trace?: AgentStep[]
  detected_language?: "en" | "hi" | "mr"
  evidence_hierarchy?: Record<string, boolean>
}

export interface StatutoryComparison {
  obligation_id: string
  dpdp_section: string
  dpdp_title: string
  dpdp_description: string
  criticality: "HIGH" | "MEDIUM" | "LOW"
  status: Exclude<ComplianceStatus, "NOT_APPLICABLE">
  severity: "HIGH" | "MEDIUM" | "LOW"
  cosine_similarity: number
  similarity_percentage: string
  matched_policy_excerpt: string
  policy_page: number
  policy_section: string
  plain_language_explanation: string
}

/** POST /api/citizen/analyze-pdf and /api/citizen/compare-similarity */
export interface PdfAnalysisReport {
  status: "SUCCESS"
  filename: string
  total_pages: number
  total_characters: number
  total_clauses_analyzed: number
  dpdp_alignment_score: number
  citizen_trust_score: number
  summary_counts: { total_statutory_obligations: number; satisfied: number; partial: number; missing: number }
  non_compliant_gaps: StatutoryComparison[]
  compliant_clauses: StatutoryComparison[]
  all_statutory_comparisons: StatutoryComparison[]
  actionable_citizen_guidance: { right: string; dpdp_basis: string; recommendation: string }[]
  duration_ms: number
}

/** POST /api/policies/generate */
export interface PolicyGenerateResponse {
  draft: string | null
  /** The saved document holding the draft (audit it by id). */
  policy_id?: string
  missing_fields?: string[]
  message?: string
  company?: string
  sector?: string
  obligations_covered?: number
  dpdp_sections_cited?: string[]
  reference_benchmarks_used?: boolean
  llm_refined?: boolean
  /** Set when the answers are too thin to draft from: what to ask, and why. */
  needs_more?: boolean
  questions?: IntakeQuestion[]
  /** Advice prompted by the answers, each with the provision it rests on. */
  recommendations?: { title: string; detail: string; basis: string }[]
  placeholders?: string[]
  drafted_with_gaps?: string[]
  /** The draft checked against the same rule book the audit applies. */
  rulebook?: { id: string; met: boolean; fixes: string[] }[]
}

export interface IntakeQuestion {
  field: string
  question: string
  why: string
  example: string
}

/** POST /api/documents/upload */
export interface DocumentUploadResponse {
  document_id: string
  status: string
  chunks?: number
  triplets?: number
  vector_count?: number
  source_type?: "LEGAL" | "POLICY"
  authority_level?: string
  message?: string
}

/** GET /api/documents/{id}/status */
export interface DocumentStatus {
  document_id: string
  status: string
  chunks?: number
  triplets?: number
}

/** GET /api/evaluation/registry/list */
export interface MetricRegistryEntry {
  key: string
  name: string
  category: EvaluationMetric["category"]
  threshold: number
}

/** GET /api/compliance */
export type AnalysisSummary = Pick<Analysis, "id" | "policy_id" | "policy_name" | "created_at" | "overall_score" | "status">