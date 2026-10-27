"""Seed a sample company privacy policy into company_policy_kb."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.ingestion.ingestion_service import ingest_document

SAMPLE_POLICY = """# Acme Fintech Privacy Policy v2.3

## Section 1: Information We Collect
We collect your name, phone number, email address, bank account details, UPI identifiers,
device information, and transaction history. We collect this information when you create an account,
make a payment, or contact support.

## Section 2: How We Use Your Data
We use your personal data to process payments, prevent fraud, verify your identity, provide customer
support, and send you service notifications. We may also use your data for limited marketing purposes
if you have separately opted in.

## Section 3: Consent
By creating an account and using our services, you consent to the collection and processing of your
personal data as described in this policy. To withdraw your consent, you must contact our support team
by email and request account deletion. We aim to process withdrawal requests within 30 days.

## Section 4: Data Retention
We retain your personal data as long as needed to provide services. Financial transaction records are
kept for 8 years to comply with regulatory and tax requirements. We may retain other data as long as
needed for business purposes.

## Section 5: Data Sharing
We share your personal data with our payment gateway partners, cloud service providers located in India,
and with government authorities when required by law. We do not sell your personal data to third parties.

## Section 6: Security
We protect your personal data using industry-standard encryption, firewalls, and access controls.
We conduct regular security audits of our systems.

## Section 7: Children
Our services are not directed at children under 18 years of age. We do not knowingly collect personal
data from children. If you believe your child has provided us personal data, please contact us.

## Section 8: Your Rights
You have the right to access, correct, and request deletion of your personal data. You may also request
a copy of the data we hold about you. Please contact our grievance officer at dpo@acmefintech.com.
We will respond to your request within 30 days.

## Section 9: Grievance
If you have any complaints about how we handle your personal data, email our Data Protection Officer
at dpo@acmefintech.com. If unsatisfied, you may escalate to the Data Protection Board of India.

## Section 10: Contact
Data Protection Officer: dpo@acmefintech.com | Grievance: +91-80000-00000
"""


async def seed_company_policy():
    from app.knowledge_base import vector_store
    vector_store.reset_for_tests()

    content = SAMPLE_POLICY.encode("utf-8")
    result = await ingest_document(
        content=content,
        filename="Acme_Fintech_Privacy_Policy_v2.3.txt",
        document_id="pol_acme_1",
        company_id="acme_fintech",
        source_type="POLICY",
        authority_level="REFERENCE",
    )

    print("\n=== COMPANY POLICY SEED RESULT ===")
    for k, v in result.items():
        if k == "pages":
            print(f"  {k}: {len(v)} pages")
        else:
            print(f"  {k}: {v}")

    company_count = vector_store.count(settings.qdrant_company_collection)
    legal_count = vector_store.count(settings.qdrant_legal_collection)
    print(f"\nCollection '{settings.qdrant_company_collection}': {company_count} vectors")
    print(f"Collection '{settings.qdrant_legal_collection}': {legal_count} vectors")

    return result


if __name__ == "__main__":
    asyncio.run(seed_company_policy())
