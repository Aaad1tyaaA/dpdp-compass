"""Extensible evaluation metric registry. Do not hard-code final research metrics."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal
import time

@dataclass
class MetricDefinition:
    name: str
    description: str
    category: Literal["base","ragas","citation","custom","guardrail"]
    direction: Literal["higher_better","lower_better"]
    threshold: float
    methodology: str = ""

class BaseMetric(ABC):
    definition: MetricDefinition
    @abstractmethod
    def compute(self, analysis: dict) -> float:
        ...

REGISTRY: dict[str, BaseMetric] = {}

def register_metric(name: str):
    def deco(cls):
        inst = cls()
        REGISTRY[name] = inst
        return cls
    return deco

# --- Real hooks (separate from inference): retrieval + evidence grounded, not constants ---
def _findings(analysis: dict) -> list[dict]:
    return analysis.get("findings", []) if isinstance(analysis, dict) else []

@register_metric("recall_at_k")
class RecallAtK(BaseMetric):
    definition = MetricDefinition("Recall@K","Fraction of required obligations retrieved","base","higher_better",0.7,"retrieval log")
    def compute(self, analysis):
        ev = analysis.get("evidence", {}) if isinstance(analysis, dict) else {}
        got = len(ev.get("legal", [])) + len(ev.get("policy", []))
        return min(1.0, got / max(1, analysis.get("top_k", 8) if isinstance(analysis, dict) else 8))

@register_metric("mrr")
class MRR(BaseMetric):
    definition = MetricDefinition("MRR","Mean reciprocal rank of first relevant evidence","base","higher_better",0.6,"retrieval scores")
    def compute(self, analysis):
        ev = (analysis.get("evidence", {}).get("legal", []) + analysis.get("evidence", {}).get("policy", [])) if isinstance(analysis, dict) else []
        for i, e in enumerate(ev):
            if (e.get("score", 0) if isinstance(e, dict) else 0) >= 0.5:
                return 1.0 / (i + 1)
        return 0.0

@register_metric("context_precision")
class ContextPrecision(BaseMetric):
    definition = MetricDefinition("Context Precision","Relevance of retrieved context","ragas","higher_better",0.75,"mean score>=0.5")
    def compute(self, analysis):
        ev = (analysis.get("evidence", {}).get("legal", []) + analysis.get("evidence", {}).get("policy", [])) if isinstance(analysis, dict) else []
        if not ev: return 0.0
        rel = sum(1 for e in ev if (e.get("score", 0) if isinstance(e, dict) else 0) >= 0.5)
        return rel / len(ev)

@register_metric("citation_accuracy")
class CitationAccuracy(BaseMetric):
    definition = MetricDefinition("Citation Accuracy","Findings with valid provenance","citation","higher_better",0.9,"citation fields present")
    def compute(self, analysis):
        fs = _findings(analysis)
        if not fs: return 0.0
        ok = sum(1 for f in fs if f.get("legal_evidence"))
        return ok / len(fs)

@register_metric("unsupported_claim_rate")
class UnsupportedClaimRate(BaseMetric):
    definition = MetricDefinition("Unsupported Claim Rate","Findings without legal evidence (lower better)","custom","lower_better",0.05,"guardrail")
    def compute(self, analysis):
        fs = _findings(analysis)
        if not fs: return 0.0
        bad = sum(1 for f in fs if not f.get("legal_evidence") and f.get("status") != "MISSING")
        return bad / len(fs)

@register_metric("faithfulness")
class Faithfulness(BaseMetric):
    definition = MetricDefinition("Faithfulness","Findings grounded in retrieved evidence","ragas","higher_better",0.8,"evidence overlap")
    def compute(self, analysis):
        fs = _findings(analysis)
        if not fs: return 0.0
        return sum(1 for f in fs if f.get("legal_evidence") and f.get("reasoning")) / len(fs)

# Extension: new research candidates (Compliance Evidence Alignment etc.) should be added as new classes
# with @register_metric and NOT presented as validated until evaluated against literature.

def run_all(analysis: dict):
    import datetime
    results=[]
    for key, metric in REGISTRY.items():
        results.append({
            "id": key,
            "name": metric.definition.name,
            "description": metric.definition.description,
            "category": metric.definition.category,
            "direction": metric.definition.direction,
            "value": metric.compute(analysis),
            "threshold": metric.definition.threshold,
            "methodology": metric.definition.methodology,
            "dataset_version": "dpdp-v1",
            "evaluated_at": datetime.datetime.utcnow().isoformat()+"Z"
        })
    return results
