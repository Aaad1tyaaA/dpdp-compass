# Trust / Compliance Methodology — deterministic, reproducible

Three separate concepts (never conflated):

1. **Evidence confidence** (per finding, 0-1): `min(1.0, 0.5 + 0.25*num_evidence + 0.25*max_relevance)`. Requires ≥1 legal citation; SATISFIED requires legal+policy.
2. **Compliance score** (0-100): `100 * (satisfied + 0.5*partial) / total`. PARTIAL=0.5, MISSING/NOT_APPLICABLE excluded from numerator. Reproducible from findings only.
3. **Risk** (per gap): severity from obligation criticality × status (MISSING>PARTIAL), likelihood HIGH if MISSING else MEDIUM, impact from penalty table (S33 up to ₹250cr). No LLM-generated numbers without evidence.

**Trust score (citizen, 0-100)** — deterministic from compliance:
`trust = clamp(30..92, 58 + (compliance_score - 50)//2)`. Documented inputs: compliance_score only. Missing evidence → findings MISSING → compliance drops → trust drops; never confident on missing data. If `legal==0 and policy==0` → withhold score, return INSUFFICIENT_EVIDENCE.

All formulas versioned here; evaluation must log `LLM_MODEL, EMBEDDING_MODEL, TOP_K, chunk config, temperature, dataset version` per experiment.
