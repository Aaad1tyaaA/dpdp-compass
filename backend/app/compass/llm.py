"""Model client for the engine: any OpenAI-compatible endpoint, temperature 0, on-disk response cache.

Caching makes a run repeatable exactly and lets an interrupted experiment resume without paying for
the same call twice. Calls and tokens are counted so cost can be reported per item.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

log = logging.getLogger(__name__)
CACHE = Path(os.environ.get("COMPASS_LLM_CACHE", Path(__file__).resolve().parents[2] / ".cache" / "llm"))


class QuotaExhausted(RuntimeError):
    """The provider's daily limit is used up on every key; waiting a few seconds will not help."""


class LLM:
    def __init__(self, model: str | None = None, extra: dict | None = None, cache: bool = True, patience: int = 40):
        from openai import OpenAI

        from app.config import reveal, settings

        self.model = model or settings.llm_model
        self.extra = {"reasoning_effort": "low"} if extra is None and self.model.startswith("openai/gpt-oss") else (extra or {})
        keys = [reveal(settings.llm_api_key) or "", *(reveal(settings.llm_fallback_api_keys) or "").split(",")]
        self.clients = [OpenAI(api_key=k.strip(), base_url=settings.llm_base_url, timeout=60, max_retries=0) for k in dict.fromkeys(keys) if k.strip()]
        self.cache, self.patience, self._turn = cache, patience, 0
        self.reset()

    def reset(self):
        self.calls = self.prompt_tokens = self.completion_tokens = self.cached = 0
        self.wait = 0.0

    @property
    def available(self) -> bool:
        return bool(self.clients)

    def complete(self, system: str, user: str, max_tokens: int = 800) -> str:
        key = hashlib.sha256(json.dumps([self.model, self.extra, system, user, max_tokens]).encode()).hexdigest()
        path = CACHE / key[:2] / f"{key}.json"
        if self.cache and path.exists():
            hit = json.loads(path.read_text(encoding="utf-8"))
            self.calls += 1
            self.cached += 1
            self.prompt_tokens += hit["prompt_tokens"]
            self.completion_tokens += hit["completion_tokens"]
            return hit["text"]
        last = None
        for attempt in range(self.patience):
            daily = 0
            for j in range(len(self.clients)):
                client = self.clients[(self._turn + j) % len(self.clients)]
                t = time.perf_counter()
                try:
                    r = client.chat.completions.create(
                        model=self.model, temperature=0, max_tokens=max_tokens, extra_body=self.extra or None,
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
                    text = r.choices[0].message.content or ""
                    self._turn += 1
                    self.calls += 1
                    self.prompt_tokens += r.usage.prompt_tokens
                    self.completion_tokens += r.usage.completion_tokens
                    if self.cache:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(json.dumps({"text": text, "prompt_tokens": r.usage.prompt_tokens, "completion_tokens": r.usage.completion_tokens,
                                                    "model": self.model, "seconds": round(time.perf_counter() - t, 3)}, ensure_ascii=False), encoding="utf-8")
                    return text
                except Exception as e:
                    last = e
                    self.wait += time.perf_counter() - t
                    msg = str(e).lower()
                    if "per day" in msg or "tpd" in msg or "rpd" in msg:
                        daily += 1
                    elif not any(t in msg for t in ("rate", "429", "connection", "timeout", "timed out", "500", "502", "503", "504")) and attempt >= 2:
                        raise  # not transient (bad request, bad key): retrying will not help
            if daily == len(self.clients):
                raise QuotaExhausted(f"Daily limit reached for {self.model} on all keys")
            time.sleep(6)
            self.wait += 6
        raise RuntimeError(f"LLM unavailable: {type(last).__name__}")


def parse_object(text: str) -> dict:
    a, b = text.find("{"), text.rfind("}")
    try:
        out = json.loads(text[a:b + 1]) if 0 <= a < b else {}
    except json.JSONDecodeError:
        out = {}
    return out if isinstance(out, dict) else {}


def parse_array(text: str) -> list:
    a, b = text.find("["), text.rfind("]")
    try:
        out = json.loads(text[a:b + 1]) if 0 <= a < b else []
    except json.JSONDecodeError:
        import re
        out = []
        for m in re.finditer(r"\{[^{}]*\}", text):  # a reply cut off at the token limit: keep the objects that completed
            try:
                out.append(json.loads(m.group()))
            except json.JSONDecodeError:
                pass
    return out if isinstance(out, list) else []
