"""Seed both DPDP Act (legal) AND a sample company policy in ONE process
so the in-memory fallback holds both collections simultaneously."""
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


async def main(pdf_path: str | None):
    from app.knowledge_base import vector_store
    vector_store.reset_for_tests()

    if pdf_path is None:
        pdf_path = r"C:\Users\Admin\Downloads\2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf"
    p = Path(pdf_path)
    legal_result = await ingest_document(
        content=p.read_bytes(), filename=p.name, document_id="dpdp_act_2023",
        source_type="LEGAL", authority_level="PRIMARY",
        source_document="DPDP Act, 2023",
    )
    print(f"LEGAL seeded: {legal_result['chunks']} chunks")

    pol_result = await ingest_document(
        content=SAMPLE_POLICY.encode("utf-8"), filename="Acme_Fintech_Privacy_Policy_v2.3.txt",
        document_id="pol_acme_1", company_id="acme_fintech",
        source_type="POLICY", authority_level="REFERENCE",
        source_document="Acme Fintech Privacy Policy v2.3",
    )
    print(f"POLICY seeded: {pol_result['chunks']} chunks")

    print(f"\nCollection counts -> legal={vector_store.count(settings.qdrant_legal_collection)} "
          f"company={vector_store.count(settings.qdrant_company_collection)}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(path))
