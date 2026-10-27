"""Regression tests for retrieval bugs that silently degraded answers (Zerodha 'how is my data kept secure?')."""
import pytest
from app.knowledge_base import vector_store
from app.retrieval.sparse_retriever import sparse_retrieve, _tokens
from app.agents.policy_generation_agent import _focus, _relevant_policy_excerpts

SECTION_8 = ("8. (1) A Data Fiduciary shall be responsible for complying with the provisions of this Act in respect of any "
             "processing undertaken by it or on its behalf by a Data Processor. (2) A Data Fiduciary may engage a Data "
             "Processor only under a valid contract. (3) Where personal data is likely to be used to make a decision, the "
             "Data Fiduciary shall ensure its completeness, accuracy and consistency. (4) A Data Fiduciary shall implement "
             "appropriate technical and organisational measures to ensure effective observance of this Act. (5) A Data "
             "Fiduciary shall protect personal data in its possession by taking reasonable security safeguards to prevent "
             "personal data breach.")


def test_stems_match_word_forms():
    assert _tokens("secure")[0] == _tokens("security")[0] == _tokens("secured")[0]


def test_keyword_index_is_built_and_finds_security_clause():
    vector_store.reset_for_tests()
    vector_store.upsert(["s8", "s7"], [SECTION_8, "7. A Data Fiduciary may process personal data for specified legitimate uses."],
                        [[1.0, 0.0], [0.0, 1.0]], [{"section": "Section 8"}, {"section": "Section 7"}])
    hits = sparse_retrieve("how is my data kept secure?")
    assert hits and hits[0]["section"] == "Section 8"


def test_focus_surfaces_the_relevant_subclause_not_just_the_start():
    f = _focus(SECTION_8, "how does zerodha keep my data secure?", budget=300)
    assert "security safeguards" in f and len(f) < len(SECTION_8)


def test_short_policy_goes_in_whole():
    clauses = [{"section": "1", "text": "We collect your PAN and bank details."},
               {"section": "5", "text": "Security: all data is encrypted with AES-256 and access is logged."}]
    assert "AES-256" in _relevant_policy_excerpts("how do you keep my data secure", clauses)


def test_long_sections_are_split_not_truncated():
    from app.ingestion.clause_chunker import clause_aware_chunk
    body = "8. " + " ".join(f"({i}) A Data Fiduciary shall do duty number {i}. " + "x " * 120 for i in range(1, 12))
    chunks = clause_aware_chunk(body, source_document="Act", max_chunk_chars=800)
    joined = " ".join(c.text for c in chunks)
    assert len(chunks) > 1 and all(len(c.text) <= 800 for c in chunks)
    assert "(11) A Data Fiduciary shall do duty number 11" in joined  # the tail used to be dropped
    assert all(c.section == chunks[0].section for c in chunks)


def test_finding_quotes_its_own_subclause():
    from app.agents.compliance_agent import _statutory_evidence
    from app.models.schemas import Obligation, RetrievedEvidence
    pool = [RetrievedEvidence(text="44. (1) In section 14 of the Telecom Regulatory Authority of India Act...", section="Section 44", source_document="Act"),
            RetrievedEvidence(text=SECTION_8 + " (6) In the event of a personal data breach, the Data Fiduciary shall give the Board intimation.", section="Section 8", source_document="Act")]
    obl = Obligation(obligation="Notify Board of breach", obligation_id="DPDP-8(6)", section="Section 8(6)", evidence=[], conditions=[], exceptions=[])
    ev = _statutory_evidence(obl, pool)
    assert ev and ev[0].citation.section == "Section 8" and ev[0].excerpt.startswith("8(6) In the event of a personal data breach")
