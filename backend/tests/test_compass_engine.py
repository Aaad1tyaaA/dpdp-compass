"""Tests for the Compass engine (app/compass): statute chunker, knowledge layers, retrieval, audit, datasets."""
import pytest

from app.compass import audit as A
from app.compass import layers, qa, statute, workflow
from app.compass.checklist import CHECKLIST, score
from eval import dpdp_qa, synth


@pytest.fixture(scope="module")
def engine():
    return A.get_engine()


def test_chunker_covers_every_section_and_keeps_provision_metadata(engine):
    assert len(engine.st.sections) == 44 and {c["section"] for c in engine.chunks} >= set(range(1, 45))
    lengths = [len(c["text"]) for c in engine.chunks if c["id"] != "schedule"]
    assert max(lengths) <= 1200
    c = next(c for c in engine.chunks if "8(5)" in c["provisions"])
    assert c["text"].startswith("Section 8. General obligations of Data Fiduciary.") and c["page"] == 7
    assert "two hundred and fifty crore rupees" in engine.st.schedule and len(engine.st.schedule_rows) == 7
    covered = {p for c in engine.chunks for p in c["provisions"]}
    assert all(u.provision in covered for u in engine.st.units(1200))  # no sub-section is lost


def test_chunking_baselines_use_the_same_text(engine):
    assert len(statute.chunk_sections(engine.st)) == 46  # 44 sections + long title + Schedule
    fixed = statute.chunk_fixed(engine.st, 600)
    assert all(len(c["text"]) <= 600 for c in fixed) and "eighteen years" in " ".join(c["text"] for c in fixed)


def test_knowledge_layers(engine):
    kb = engine.kb
    assert len(kb.definitions) == 28 and kb.definitions["child"] == "2(f)"
    duties = [o for o in kb.obligations if o["provision"] == "8(5)"]
    assert duties and duties[0]["actor"] == "Data Fiduciary" and duties[0]["predicate"] == "MUST" and duties[0]["principle"] == "security safeguards"
    assert any(o["predicate"] == "MUST_NOT" and o["provision"] == "9(3)" for o in kb.obligations)
    assert any(o["predicate"] == "HAS_RIGHT" and o["provision"] == "6(4)" for o in kb.obligations)
    # an actor inside a prepositional phrase is not a subject: 5(1) "a notice given by the Data Fiduciary"
    assert not any(o["provision"] == "5(1)" for o in kb.obligations)
    assert all(e.sentence and e.provision for e in kb.edges)  # every edge carries provenance
    assert layers.penalty_ceiling(kb, "8(5)").startswith("May extend to two hundred and fifty crore")
    assert layers.penalty_ceiling(kb, "5(1)").startswith("May extend to fifty crore")


def test_cross_references_skip_other_acts():
    assert layers.references("under sub-section (4) of section 6 and section 13", 5) == ["6(4)", "13"]
    assert layers.references("section 14 of the Telecom Regulatory Authority of India Act, 1997", 2) == []
    assert layers.references("referred to in sub-sections (1) and (2)", 5) == ["5(1)", "5(2)"]


def test_dpdp_qa_is_valid_and_split_is_stable(engine):
    items = dpdp_qa.load()
    assert dpdp_qa.validate(items, engine.st) == []
    assert len(items) == 198 and sum(i["split"] == "dev" for i in items) == 60
    assert all(i["split"] == next(s["split"] for s in items if s["id"] == i["source"]) for i in items if i["source"])
    assert dpdp_qa.dataset_hash(items) == dpdp_qa.dataset_hash(dpdp_qa.load())


def test_retrieval_finds_the_gold_provision(engine):
    items = {i["phrase"]: i for i in dpdp_qa.load() if i["lang"] == "en" and i["answerable"]}
    for phrase in ("obtain verifiable consent of the parent", "two hundred and fifty crore rupees", "within a period of sixty days"):
        hits, _ = engine.index.search(items[phrase]["question"], k=5)
        assert any(dpdp_qa.relevant(h["text"], items[phrase]) for h in hits), phrase


def test_metadata_lookup_fetches_a_named_provision(engine):
    hits, _ = engine.index.search("What does section 16(1) say?", k=3, weights={"metadata": 1.0}, rerank=False)
    assert hits and "16(1)" in hits[0]["provisions"] and hits[0]["sources"] == ["metadata"]


def test_synth_labels_are_known_by_construction():
    a, b = synth.generate(), synth.generate()
    assert synth.dataset_hash(a) == synth.dataset_hash(b) and len(a) == 40 and sum(p["injected"] for p in a) == 8
    p = a[0]
    assert set(p["labels"]) == {o["id"] for o in CHECKLIST}
    assert all((p["kinds"][k] in ("absent", "hard_negative")) == (v == "Missing") for k, v in p["labels"].items())


def test_guardrails_correct_unverifiable_findings(engine):
    policy = "We protect personal data with encryption in transit and at rest and role-based access controls."
    mapping = A.map_obligations(engine)
    verdicts = {"SECURITY": {"id": "SECURITY", "status": "Satisfied", "quote": "encryption in transit and at rest", "confidence": 0.9},
                "BREACH": {"id": "BREACH", "status": "Satisfied", "quote": "we notify the Board within 72 hours", "confidence": 1.7},  # invented quote
                "ERASURE": {"id": "ERASURE", "status": "Partial", "quote": "", "confidence": 0.6}}
    f = {x["id"]: x for x in A.apply_guardrails(verdicts, policy, mapping, engine)}
    assert f["SECURITY"]["status"] == "Satisfied" and f["SECURITY"]["quote_verified"] and f["SECURITY"]["citation"] == "DPDP Act, Section 8(5)"
    assert f["BREACH"]["status"] == "Missing" and {"quote_verbatim", "partial_needs_evidence", "schema"} <= set(f["BREACH"]["guardrail_flags"])
    assert f["ERASURE"]["status"] == "Missing" and f["NOTICE"]["status"] == "Missing" and "schema" in f["NOTICE"]["guardrail_flags"]


def test_score_formula():
    assert score(["Satisfied", "Partial", "Missing", "Not applicable"]) == 50.0


def test_workflow_audit_without_a_model_uses_keyword_rules():
    out = workflow.run(policy=synth.generate()[0]["text"], llm=None)
    assert out["intent"] == "audit" and len(out["findings"]) == 14 and out["judge"] == "keyword rules"
    assert [s["agent"] for s in out["trace"]] == ["orchestrator", "retrieval", "obligation_mapping", "compliance", "guardrails", "risk"]
    assert all(f["citation"].startswith("DPDP Act, Section") and f["penalty_ceiling"] for f in out["findings"])


def test_workflow_question_redacts_and_routes(engine):
    out = workflow.run("My name is Rahul Sharma. What does section 9(3) prohibit?", llm=None)
    assert out["intent"] == "question" and out["redactions"] == {"NAME": 1} and "9(3)" in out["citations"]
    assert [s["agent"] for s in out["trace"]] == ["orchestrator", "answer"]


def test_citation_parsing_and_language_detection():
    assert qa.cited_provisions("Yes [Section 9(1)]; see also Section 2(f) and the [Schedule].") == ["9(1)", "2(f)", "Schedule"]
    assert qa.same_provision("8(7)", "8(7)(a)") and not qa.same_provision("8(7)", "8(6)")
    assert qa.detect_language("Who is a child?") == "en" and qa.detect_language("बालक कौन है?") == "hi"
    assert qa.detect_language("'वैयक्तिक डेटा' म्हणजे काय?") == "mr"


def test_workflow_degrades_when_the_model_is_unavailable():
    class Down:
        calls = wait = prompt_tokens = completion_tokens = 0
        def complete(self, *a, **k):
            raise RuntimeError("provider down")
    audit = workflow.run(policy=synth.generate()[0]["text"], llm=Down())
    assert audit["judge"] == "keyword rules" and "model unavailable" in audit["degraded"] and len(audit["findings"]) == 14
    ask = workflow.run("What does section 9(3) prohibit?", llm=Down())
    assert ask["mode"] == "extractive" and "model unavailable" in ask["degraded"] and "9(3)" in ask["citations"]
