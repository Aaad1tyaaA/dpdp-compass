"""Model discovery — queries OpenRouter catalog, ranks for LEGAL RAG + reasoning + structured output.
Usage: python -m app.services.model_discovery  (needs OPENROUTER_API_KEY or LLM_API_KEY; works offline with fallback list)
Never prints keys.
"""
import os
import sys

FALLBACK_CANDIDATES = [
    {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "provider": "nvidia", "free": True, "context": 256000, "reasoning": True, "structured": True, "tools": True},
    {"id": "google/gemini-2.0-flash:free", "provider": "google", "free": True, "context": 1000000, "reasoning": True, "structured": True, "tools": True},
    {"id": "meta-llama/llama-3.1-70b:free", "provider": "meta", "free": True, "context": 128000, "reasoning": False, "structured": True, "tools": True},
    {"id": "openrouter/free", "provider": "openrouter", "free": True, "context": 64000, "reasoning": False, "structured": False, "tools": False},
]

def score_candidate(m: dict) -> tuple[int, str]:
    s = 0; reasons = []
    if m.get("free"): s += 3; reasons.append("free")
    ctx = m.get("context", 0) or 0
    if ctx >= 128000: s += 2; reasons.append(f"ctx={ctx}")
    elif ctx >= 32000: s += 1
    if m.get("reasoning"): s += 2; reasons.append("reasoning")
    if m.get("structured"): s += 2; reasons.append("structured-out")
    if m.get("tools"): s += 1; reasons.append("tools")
    return s, "+".join(reasons)

def fetch_catalog(api_key: str) -> list[dict]:
    import urllib.request, json
    req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    out = []
    for m in data.get("data", []):
        mid = m.get("id", "")
        pricing = m.get("pricing", {})
        free = str(pricing.get("prompt", "1")).strip() in ("0", "0.0", "0.000000") and str(pricing.get("completion", "1")).strip() in ("0", "0.0", "0.000000")
        out.append({"id": mid, "provider": mid.split("/")[0] if "/" in mid else "?",
                    "free": free, "context": m.get("context_length", 0),
                    "reasoning": bool(m.get("supports_reasoning") or "reasoning" in str(m.get("supported_parameters", []))),
                    "structured": "response_format" in (m.get("supported_parameters") or []),
                    "tools": "tools" in (m.get("supported_parameters") or [])})
    return out

def main():
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_API_KEY") or ""
    models: list[dict] = []
    if key:
        try:
            models = fetch_catalog(key)
            print(f"Fetched {len(models)} models from OpenRouter")
        except Exception as e:
            print(f"Catalog fetch failed ({type(e).__name__}), using fallback list")
    if not models:
        models = FALLBACK_CANDIDATES
        print("Using offline fallback candidates (no key or offline)")
    # Filter free text-in/out
    free = [m for m in models if m.get("free")]
    print(f"\nFREE MODELS: {len(free)} / {len(models)}")
    scored = [(score_candidate(m)[0], score_candidate(m)[1], m) for m in free]
    ranked = sorted(scored, key=lambda x: x[0], reverse=True)
    print(f"{'Model':55} {'Ctx':>8} {'Reas':>5} {'Struct':>6} {'Tools':>5} {'Score':>5}  Why")
    for score, why, m in ranked[:15]:
        print(f"{m['id'][:55]:55} {m.get('context',0):>8} {str(m.get('reasoning')):>5} {str(m.get('structured')):>6} {str(m.get('tools')):>5} {score:>5}  {why}")
    if ranked:
        best = ranked[0][2]
        print(f"\nRecommended for project: {best['id']} — Reason: {ranked[0][1]} (legal RAG + multi-step reasoning + long context)")
        print("Pin for research: LLM_MODEL=" + best["id"])
        print("Dev fallback: openrouter/free (non-reproducible)")
    print("\nNote: free status changes; re-run before experiments. Never commit keys.")

if __name__ == "__main__":
    sys.exit(main())
