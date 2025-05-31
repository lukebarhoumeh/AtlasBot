import time

# ruff: noqa: E402

time.sleep = lambda *_a, **_k: None  # all sleeps are instant in tests  # noqa: E402

import os
import sys
import types
from pathlib import Path

import pkg_resources
import pytest

for name in ("dotenv", "boto3", "openai", "requests", "websocket"):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
if not hasattr(sys.modules["dotenv"], "load_dotenv"):
    sys.modules["dotenv"].load_dotenv = lambda *a, **k: None
if not hasattr(sys.modules["boto3"], "session"):
    sys.modules["boto3"].session = types.SimpleNamespace(
        Session=lambda *a, **k: types.SimpleNamespace(
            client=lambda *_a, **_k: types.SimpleNamespace(
                get_secret_value=lambda SecretId: {}
            )
        )
    )
openai_stub = sys.modules["openai"]
error_mod = types.ModuleType("openai.error")


class _Dummy(Exception):
    pass


class RateLimitError(_Dummy):
    pass


class APIError(_Dummy):
    pass


error_mod.RateLimitError = RateLimitError
error_mod.APIError = APIError
openai_stub.error = error_mod
openai_stub.RateLimitError = RateLimitError
openai_stub.APIError = APIError
openai_stub.OpenAI = lambda *a, **k: types.SimpleNamespace(
    api_key=k.get("api_key", ""),
    chat=types.SimpleNamespace(
        completions=types.SimpleNamespace(
            create=lambda *_a, **_k: types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(message=types.SimpleNamespace(content="{}"))
                ]
            )
        )
    ),
)

req_stub = sys.modules["requests"]
req_stub.post = lambda *_a, **_k: types.SimpleNamespace(
    status_code=200, json=lambda: {}
)
req_stub.get = lambda *_a, **_k: types.SimpleNamespace(ok=True, json=lambda: {})

ws_stub = sys.modules["websocket"]
ws_stub.WebSocketApp = lambda *a, **k: types.SimpleNamespace(
    send=lambda *_a, **_k: None,
    run_forever=lambda *_a, **_k: None,
    close=lambda *_a, **_k: None,
)
ws_stub._exceptions = types.SimpleNamespace(WebSocketBadStatusException=Exception)


class DummyMarket:
    def minute_bars(self, _sym):
        return [(1, 1, 1, 1)] * 60

    def latest_trade(self, _sym):
        return 100.0

    def wait_ready(self, _timeout=0):
        return True


@pytest.fixture(autouse=True)
def patch_market(monkeypatch):
    if os.getenv("USE_REAL_MD"):
        yield
        return
    import atlasbot.signals as sig

    dummy = DummyMarket()
    monkeypatch.setattr("atlasbot.market_data.get_market", lambda symbols=None: dummy)
    monkeypatch.setattr("atlasbot.utils._get_md", lambda: dummy, raising=False)
    sig.momentum.__globals__["get_market"] = lambda symbols=None: dummy
    sig.breakout.__globals__["get_market"] = lambda symbols=None: dummy
    yield


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for pkg in ("pandas", "requests", "ccxt"):
    if not pkg_resources.working_set.by_key.get(pkg):
        dist = pkg_resources.Distribution(project_name=pkg, version="0.0")
        pkg_resources.working_set.add(dist)

os.environ.setdefault("ATLAS_TEST", "1")
