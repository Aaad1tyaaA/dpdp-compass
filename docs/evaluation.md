# Evaluation Architecture

Extensible metric registry: `backend/app/evaluation/registry.py`

- Implement `BaseMetric` with `MetricDefinition` (name, description, category, direction, threshold, methodology)
- Decorate with `@register_metric("my_metric_id")`
- `run_all(analysis)` auto-discovers.

Categories: `base` | `ragas` | `citation` | `custom` | `guardrail`
Built-ins: Context Precision, Context Recall, Faithfulness, Citation Accuracy, Unsupported Claim Rate

Research candidates (Compliance Evidence Alignment, Evidence sufficiency, Evidence-to-decision consistency, Risk calibration, Rights preservation) are NOT validated — add via registry when paper finalizes thresholds/methodology. Do not claim novel until validated vs literature.

Guardrails: `backend/app/guardrails/engine.py` — append callables to `REGISTRY`. Each returns GuardrailResult. High-risk with insufficient evidence → INSUFFICIENT_EVIDENCE.

Logging: every analysis stores query, retrieved docs/clauses, obligations, evidence, decision, confidence, citations, risk, guardrail, latency, tokens, metrics, model/provider/version, timestamp for reproducibility.