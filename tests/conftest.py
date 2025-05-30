import importlib
import os
import sys
import types
from pathlib import Path

import pkg_resources
import pytest

for name in (
    "openai",
    "websocket",
    "requests",
    "dotenv",
    "boto3",
    "pandas",
    "numpy",
    "prometheus_client",
):
    if name not in sys.modules:
        sys.modules[name] = importlib.import_module("types").SimpleNamespace()
if not hasattr(sys.modules["dotenv"], "load_dotenv"):
    sys.modules["dotenv"].load_dotenv = lambda *a, **k: None
if not hasattr(sys.modules["openai"], "ChatCompletion"):
    sys.modules["openai"].ChatCompletion = types.SimpleNamespace()


def _dummy_create(*a, **k):
    return types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="{}"))]
    )


sys.modules["openai"].ChatCompletion.create = _dummy_create
if not hasattr(sys.modules["openai"], "OpenAI"):
    sys.modules["openai"].OpenAI = lambda *a, **k: types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=_dummy_create)
        )
    )
if not hasattr(sys.modules["boto3"], "session"):
    sys.modules["boto3"].session = types.SimpleNamespace(
        Session=lambda *a, **k: types.SimpleNamespace(
            client=lambda *a, **k: types.SimpleNamespace(
                get_secret_value=lambda SecretId: {}
            )
        )
    )
if not hasattr(sys.modules["pandas"], "DataFrame"):

    class _DF:
        def __init__(self, rows):
            self.rows = rows

        def to_csv(self, path, mode="w", header=True, index=False):
            import csv

            exists = "a" in mode and os.path.exists(path)
            with open(path, mode, newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.rows[0].keys())
                if header and not exists:
                    writer.writeheader()
                for r in self.rows:
                    writer.writerow(r)

    sys.modules["pandas"].DataFrame = _DF
if not hasattr(sys.modules["numpy"], "corrcoef"):

    def _corrcoef(a, b):
        import math

        if len(a) != len(b):
            raise ValueError
        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b)) / len(a)
        var_a = sum((x - mean_a) ** 2 for x in a) / len(a)
        var_b = sum((y - mean_b) ** 2 for y in b) / len(b)
        if var_a == 0 or var_b == 0:
            return [[1.0, 0.0], [0.0, 1.0]]
        corr = cov / math.sqrt(var_a * var_b)
        return [[1.0, corr], [corr, 1.0]]

    sys.modules["numpy"].corrcoef = _corrcoef
if not hasattr(sys.modules["prometheus_client"], "Gauge"):
    ns = types.SimpleNamespace
    sys.modules["prometheus_client"].Gauge = lambda *a, **k: ns(
        inc=lambda *a, **k: None, set=lambda *a, **k: None
    )
    sys.modules["prometheus_client"].Counter = lambda *a, **k: ns(
        inc=lambda *a, **k: None
    )
    sys.modules["prometheus_client"].CollectorRegistry = object
    sys.modules["prometheus_client"].Histogram = lambda *a, **k: ns(
        observe=lambda *a, **k: None
    )
    sys.modules["prometheus_client"].start_http_server = lambda *a, **k: None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


for pkg in ("pandas", "requests", "ccxt"):
    if not pkg_resources.working_set.by_key.get(pkg):
        dist = pkg_resources.Distribution(project_name=pkg, version="0.0")
        pkg_resources.working_set.add(dist)

os.environ.setdefault("ATLAS_TEST", "1")


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


@pytest.fixture(autouse=True)
def stub_net_calls(monkeypatch):
    monkeypatch.setattr(
        "requests.post",
        lambda *a, **k: types.SimpleNamespace(status_code=200, json=lambda: {}),
        raising=False,
    )
    for mod in ("openai", "websocket"):
        if mod not in sys.modules:
            sys.modules[mod] = importlib.import_module("types").SimpleNamespace()
    import openai

    monkeypatch.setattr(
        openai.ChatCompletion,
        "create",
        lambda *a, **k: types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="{}"))]
        ),
        raising=False,
    )
    import websocket

    monkeypatch.setattr(
        websocket,
        "WebSocketApp",
        lambda *a, **k: types.SimpleNamespace(
            send=lambda *a, **k: None,
            run_forever=lambda *a, **k: None,
            close=lambda *a, **k: None,
        ),
        raising=False,
    )
    yield
