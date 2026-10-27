"""Automated check of extracted deontic triplets: an LLM reads each triplet against its source sentence.

    python -m eval.triplet_check

This is not a human annotation. Writes eval/results/triplets.json.
"""
from __future__ import annotations

import random

from app.compass.llm import LLM, parse_object

from .common import ci, corpus, save

MODEL = "qwen/qwen3.8-27b"
SYSTEM = (
    "You check a triplet extracted from a sentence of a statute. The triplet is (actor, modality, action): the actor is the "
    "grammatical subject on whom the sentence places the duty, prohibition, right or power; modality is MUST (shall), "
    "MUST_NOT (shall not), HAS_RIGHT (shall have the right) or MAY (may); action is what the actor must, must not or may do "
    "(it may be cut short). Reply with ONLY a JSON object: "
    '{"correct": true | false, "error": "none" | "subject" | "modality" | "object"}. '
    "A leading condition of the sentence (such as 'by notification' or 'within a reasonable time') may have been moved out of "
    "the action into a separate condition field; that is correct. "
    "correct = the actor is the subject of that modal verb in the sentence, the modality matches, and the action states what "
    "the actor must, must not or may do. Use error=object if the action is a condition or fragment and not the act itself."
)


def main(n: int = 60, seed: int = 2023):
    _, kb = corpus()
    sample = random.Random(seed).sample(kb.obligations, min(n, len(kb.obligations)))
    llm = LLM(model=MODEL, extra={"reasoning_effort": "none"})
    rows = []
    for o in sample:
        v = parse_object(llm.complete(SYSTEM, f"SENTENCE\n{o['sentence']}\n\nTRIPLET\nactor: {o['actor']}\nmodality: {o['predicate']}\naction: {o['action']}\ncondition: {o.get('condition') or '(none)'}", 60))
        rows.append({"id": o["id"], "provision": o["provision"], "actor": o["actor"], "predicate": o["predicate"], "action": o["action"][:120],
                     "correct": bool(v.get("correct")), "error": v.get("error", "unparsed")})
    ok = [float(r["correct"]) for r in rows]
    lo, hi = ci(ok)
    errors = {}
    for r in rows:
        if not r["correct"]:
            errors[r["error"]] = errors.get(r["error"], 0) + 1
    out = {"model": MODEL, "population": len(kb.obligations), "sampled": len(rows), "correct": int(sum(ok)), "precision": round(sum(ok) / len(ok), 3),
           "ci95": [round(lo, 2), round(hi, 2)], "errors": errors, "rows": rows}
    save("triplets.json", out)
    print({k: v for k, v in out.items() if k != "rows"})
    for r in rows:
        if not r["correct"]:
            print(" x", r["provision"], r["actor"], r["predicate"], "|", r["action"][:80], "|", r["error"])


if __name__ == "__main__":
    main()
