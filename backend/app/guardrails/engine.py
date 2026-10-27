"""Extensible guardrail middleware. Each guardrail is a callable returning GuardrailResult."""
from app.models.schemas import Severity
import re

# Known legal sources for citation validation
KNOWN_SOURCES = {"DPDP Act, 2023", "DPDP Act", "DPDP Rules, 2025", "DPDP Rules", "Regulatory Guidelines"}

def guardrail_citation_exists(findings):
    results=[]
    for f in findings:
        has_citation = bool(f.get("legal_evidence")) or bool(f.get("policy_evidence"))
        results.append({
            "id": f"gr_citation_{f.get('id')}",
            "rule": "Citation must exist",
            "passed": has_citation or f.get("status")=="MISSING",
            "severity": Severity.HIGH,
            "reason": "Finding has citations" if has_citation else "No evidence cited" if f.get("status")!="MISSING" else "MISSING correctly has no policy evidence",
            "recommendation": None if has_citation else "Add citation or mark INSUFFICIENT_EVIDENCE"
        })
    return results

def guardrail_high_risk_evidence(findings):
    results=[]
    for f in findings:
        if f.get("status") in ["MISSING","PARTIAL"]:
            ev = (f.get("policy_evidence") or []) + (f.get("legal_evidence") or [])
            sufficient = len(ev) >= 2 or any(e.get("relevance_score",0)>0.85 for e in ev) if ev else False
            results.append({
                "id": f"gr_highrisk_{f.get('id')}",
                "rule": "High-risk requires sufficient evidence",
                "passed": sufficient,
                "severity": Severity.HIGH,
                "reason": "Sufficient evidence" if sufficient else "Single weak evidence for high-risk finding",
                "recommendation": None if sufficient else "Add corroborating clause"
            })
    return results

def guardrail_hallucinated_citation(findings):
    results=[]
    for f in findings:
        for ev in list(f.get("legal_evidence",[])) + list(f.get("policy_evidence",[])):
            cit = ev.get("citation",{})
            src = cit.get("source_document","") if isinstance(cit, dict) else getattr(cit, "source_document", "")
            # Check if source looks hallucinated (not in known and not policy)
            is_policy = (cit.get("type")=="POLICY" if isinstance(cit, dict) else True)
            if not is_policy and src and src not in KNOWN_SOURCES:
                # Allow if contains DPDP but not exact
                if "DPDP" not in src:
                    results.append({"id": f"gr_hall_cit_{f.get('id')}", "rule": "Hallucinated citation", "passed": False, "severity": Severity.HIGH, "reason": f"Citation source '{src}' not in allow-list", "recommendation": "Replace with valid DPDP source"})
                    break
    if not results:
        results.append({"id": "gr_hall_cit_global", "rule": "Hallucinated citation", "passed": True, "severity": Severity.HIGH, "reason": "All citations to known sources"})
    return results

def guardrail_confidence_range(findings):
    results=[]
    for f in findings:
        try:
            c = float(f.get("confidence",0))
            passed = 0 <= c <= 1
        except Exception:
            passed=False
            c="invalid"
        results.append({"id": f"gr_conf_{f.get('id')}", "rule": "Confidence 0-1", "passed": passed, "severity": Severity.MEDIUM, "reason": f"Confidence {c} {'in range' if passed else 'out of range'}", "recommendation": None if passed else "Clamp confidence 0-1"})
    if not findings:
        results.append({"id": "gr_conf_empty", "rule": "Confidence 0-1", "passed": True, "severity": Severity.MEDIUM, "reason": "No findings"})
    return results

def guardrail_malformed_output(findings):
    results=[]
    required = ["id","obligation_title","status","reasoning","legal_evidence"]
    for f in findings:
        missing=[k for k in required if k not in f]
        results.append({"id": f"gr_malform_{f.get('id')}", "rule": "Malformed structured output", "passed": not missing, "severity": Severity.MEDIUM, "reason": "All required fields present" if not missing else f"Missing {missing}", "recommendation": None if not missing else "Fix agent output schema"})
    if not findings:
        results.append({"id": "gr_malform_empty", "rule": "Malformed structured output", "passed": True, "severity": Severity.MEDIUM, "reason": "No findings to check"})
    return results

def guardrail_prompt_injection(findings):
    pattern = re.compile(r"ignore previous instructions|system:\s|jailbreak|do anything now", re.I)
    results=[]
    for f in findings:
        for ev in list(f.get("legal_evidence",[])) + list(f.get("policy_evidence",[])):
            txt = (ev.get("excerpt") or ev.get("text") or "")[:800]
            if pattern.search(txt):
                results.append({"id": f"gr_inject_{f.get('id')}", "rule": "Prompt injection in retrieved doc", "passed": False, "severity": Severity.HIGH, "reason": "Retrieved excerpt contains imperative instruction — must be treated as DATA only", "recommendation": "Sanitize retrieved text, do not follow instructions inside"})
                break
    if not results:
        results.append({"id": "gr_inject_global", "rule": "Prompt injection in retrieved doc", "passed": True, "severity": Severity.HIGH, "reason": "No injection detected"})
    return results

def guardrail_unsupported_claim(findings):
    # Every MISSING/PARTIAL must have at least one legal_evidence; SATISFIED must have both
    results=[]
    for f in findings:
        status=f.get("status")
        has_legal=bool(f.get("legal_evidence"))
        has_policy=bool(f.get("policy_evidence"))
        if status=="SATISFIED" and not (has_legal and has_policy):
            passed=False
            reason="SATISFIED requires both legal + policy evidence"
        elif status in ("PARTIAL","MISSING") and not has_legal:
            passed=False
            reason=f"{status} requires legal evidence"
        else:
            passed=True
            reason="Evidence supports claim"
        results.append({"id": f"gr_unsupported_{f.get('id')}", "rule": "Unsupported compliance finding", "passed": passed, "severity": Severity.HIGH, "reason": reason})
    if not findings:
        results.append({"id": "gr_unsupported_empty", "rule": "Unsupported compliance finding", "passed": True, "severity": Severity.HIGH, "reason": "No findings"})
    return results

REGISTRY = [guardrail_citation_exists, guardrail_high_risk_evidence, guardrail_hallucinated_citation, guardrail_confidence_range, guardrail_malformed_output, guardrail_prompt_injection, guardrail_unsupported_claim]

def run_guardrails(findings: list[dict]) -> list[dict]:
    out=[]
    for fn in REGISTRY:
        try:
            out.extend(fn(findings))
        except Exception as e:
            out.append({"id": f"gr_err_{fn.__name__}", "rule": fn.__name__, "passed": False, "severity": Severity.MEDIUM, "reason": f"Guardrail error: {e}"})
    # Deduplicate by id, keep first
    seen=set()
    uniq=[]
    for r in out:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    return uniq
