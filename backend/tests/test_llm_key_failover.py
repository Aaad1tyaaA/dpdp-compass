import asyncio
from types import SimpleNamespace

from app.services.llm_gateway import RobustOpenRouterProvider


class _Completions:
    def __init__(self, name, calls, fail):
        self.name, self.calls, self.fail = name, calls, fail

    async def create(self, model, **_):
        self.calls.append((self.name, model))
        if self.fail:
            raise Exception("Error code: 429 - rate limit reached")
        msg = SimpleNamespace(content=f"ok from {self.name}")
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=None)


def test_rate_limited_primary_key_fails_over_to_backup_key_same_model():
    p = RobustOpenRouterProvider(api_key="k1", backup_keys=["k2"], base_url="http://x", primary_model="big", fallbacks=["small"])
    calls = []
    p.clients = [SimpleNamespace(chat=SimpleNamespace(completions=_Completions(n, calls, fail=(n == "k1")))) for n in ("k1", "k2")]
    out = asyncio.run(p.complete_with_meta("q"))
    assert out["text"] == "ok from k2"
    # Best model on the backup key is tried before the weaker fallback model.
    assert calls == [("k1", "big"), ("k2", "big")]
