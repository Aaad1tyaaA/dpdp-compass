"""Seed DPDP + company policy, then run a LIVE business audit end-to-end."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import importlib.util
_spec = importlib.util.spec_from_file_location("seed_all", Path(__file__).resolve().parent / "seed_all.py")
_seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_seed)
seed_main = _seed.main

SAMPLE_POLICY_TEXT = """# Acme Fintech Privacy Policy v2.3
We collect your name, phone number, bank account details, UPI identifiers, and transaction history
when you create an account, make a payment, or contact support.
We use your personal data to process payments, prevent fraud, verify your identity, provide customer
support, and send you service notifications.
By creating an account, you consent to the collection and processing of your personal data. To withdraw
your consent, you must contact our support team by email and request account deletion. We aim to process
withdrawal requests within 30 days.
We retain your personal data as long as needed to provide services. Financial transaction records are
kept for 8 years to comply with regulatory and tax requirements.
We share your personal data with our payment gateway partners, cloud service providers located in India,
and with government authorities when required by law. We do not sell your personal data.
We protect your personal data using industry-standard encryption, firewalls, and access controls.
Our services are not directed at children under 18 years of age. We do not knowingly collect personal data
from children.
You have the right to access, correct, and request deletion of your personal data. Contact our grievance
officer at dpo@acmefintech.com. We will respond within 30 days.
If you have complaints, email our DPO. If unsatisfied, escalate to the Data Protection Board of India.
Data Protection Officer: dpo@acmefintech.com | Grievance: +91-80000-00000
"""


async def run():
    await seed_main(r"C:\Users\Admin\Downloads\2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf")

    from app.config import settings
    settings.mock_llm = False  # live inference

    from app.agents.orchestrator import orchestrate
    res = await orchestrate(
        query="audit this policy against DPDP obligations",
        mode="business",
        policy_text=SAMPLE_POLICY_TEXT,
        policy_id="acme_fintech",
    )
    print("\n=== LIVE BUSINESS AUDIT ===")
    print("status:", res.get("status"))
    print("evidence_status:", res.get("evidence_status"))
    print("model_used:", res.get("model_used"))
    print("findings count:", len(res.get("findings", [])))
    print("risks count:", len(res.get("risks", [])))
    print("citations count:", len(res.get("citations", [])))
    print("iterations:", res.get("iterations"))
    print("trace agents:", [t.get("agent") for t in res.get("trace", [])])
    print("\n--- FINDINGS ---")
    for f in res.get("findings", []):
        print(f"  [{f.get('status')}/{f.get('severity')}] {f.get('obligation_title','')[:60]}")
        print(f"      reasoning: {f.get('reasoning','')[:120]}")
    print("\n--- GUARDRAILS ---")
    for g in res.get("guardrails", []):
        print(f"  [{'PASS' if g.get('passed') else 'FAIL'}] {g.get('rule')}: {g.get('reason','')[:80]}")


if __name__ == "__main__":
    asyncio.run(run())
