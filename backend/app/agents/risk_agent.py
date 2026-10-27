"""5. Risk Assessment Agent — evidence-grounded severity/impact/likelihood."""
import logging
from typing import List
from app.models.schemas import ComplianceFinding, RiskAssessment, Severity
from app.services.llm import get_llm
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM = """You are the Risk Assessment Agent. For each compliance gap, determine severity, impact, likelihood, rationale, recommendation.
Be evidence-grounded. Do not inflate scores without citation. Return JSON array."""

def heuristic_risk(finding: ComplianceFinding) -> RiskAssessment:
    # Evidence-grounded mapping — no arbitrary feel
    sev = finding.severity
    impact_map = {
        Severity.CRITICAL: "Regulatory penalty up to ₹250cr, Board inquiry, user trust loss",
        Severity.HIGH: "Penalty up to ₹150cr, audit risk",
        Severity.MEDIUM: "Remediation required, potential user complaints",
        Severity.LOW: "Minor gap, document fix",
        Severity.INFO: "Advisory",
    }
    likelihood = "HIGH" if finding.status == "MISSING" else "MEDIUM" if finding.status == "PARTIAL" else "LOW"  # type: ignore
    return RiskAssessment(
        finding_id=finding.id,
        severity=sev,
        impact=impact_map.get(sev, "Impact"),
        likelihood=likelihood,  # type: ignore
        rationale=f"{finding.obligation_id} is {finding.status}; {finding.reasoning[:120]}",
        recommendation=finding.recommended_action,
    )

async def assess_risks(findings: List[ComplianceFinding], use_llm: bool = True) -> List[RiskAssessment]:
    if not use_llm or settings.mock_llm or not (settings.llm_api_key or settings.openai_api_key):
        return [heuristic_risk(f) for f in findings if f.status != "SATISFIED"]

    llm = get_llm()
    gaps = [f for f in findings if f.status in ("MISSING","PARTIAL")]
    if not gaps:
        return []
    import json
    prompt = json.dumps([{"id": f.id, "obligation": f.obligation_title, "status": f.status, "severity": f.severity.value if hasattr(f.severity,'value') else str(f.severity), "reasoning": f.reasoning[:200]} for f in gaps])
    try:
        raw = await llm.complete(f"Gaps:\n{prompt}\n\nReturn JSON array with finding_id, severity, impact, likelihood, rationale, recommendation.", system=SYSTEM)
        import re
        m = re.search(r"\[.*\]", raw, re.S)
        data = json.loads(m.group(0)) if m else []
        out=[]
        finding_by_id = {f.id: f for f in gaps}
        for item in data:
            # Validate against evidence — don't allow invented high severity without basis
            finding = finding_by_id.get(item.get("finding_id"), gaps[0])
            sev = str(item.get("severity") or finding.severity or "MEDIUM").upper()
            if hasattr(finding.severity, "value"):
                evidence_sev = finding.severity.value
            else:
                evidence_sev = str(finding.severity)
            # Never let the LLM invent a milder grade than the evidence-backed finding
            rank = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
            if rank.get(evidence_sev, 2) > rank.get(sev, 2):
                sev = evidence_sev
            if sev not in ("CRITICAL","HIGH","MEDIUM","LOW","INFO"):
                sev = evidence_sev if evidence_sev in ("CRITICAL","HIGH","MEDIUM","LOW","INFO") else "MEDIUM"
            out.append(RiskAssessment(
                finding_id=item.get("finding_id", finding.id),
                severity=sev,  # type: ignore
                impact=item.get("impact","Impact")[:300],
                likelihood=item.get("likelihood","MEDIUM"),  # type: ignore
                rationale=item.get("rationale","Evidence-grounded")[:400],
                recommendation=item.get("recommendation","Remediate"),
            ))
        logger.info("risk_agent llm n=%d", len(out))
        return out or [heuristic_risk(f) for f in gaps]
    except Exception as e:
        logger.warning("risk_agent fallback %s", e)
        return [heuristic_risk(f) for f in gaps]
