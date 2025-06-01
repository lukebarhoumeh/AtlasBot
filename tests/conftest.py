# --- lightweight stubs so offline CI can import without wheels ---
import csv
import os
import sys
import types
from pathlib import Path

import pkg_resources
import pytest

for _name in ("numpy", "pandas", "prometheus_client"):
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)

numpy_stub = sys.modules["numpy"]
if not hasattr(numpy_stub, "corrcoef"):

    def corrcoef(a, b):
        n = float(len(a))
        if n == 0:
            return [[1.0, 0.0], [0.0, 1.0]]
        ma = sum(a) / n
        mb = sum(b) / n
        cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        var_a = sum((x - ma) ** 2 for x in a)
        var_b = sum((y - mb) ** 2 for y in b)
        denom = (var_a * var_b) ** 0.5
        c = 0.0 if denom == 0 else cov / denom
        return [[1.0, c], [c, 1.0]]

    numpy_stub.corrcoef = corrcoef
    numpy_stub.isscalar = lambda x: isinstance(x, (int, float))


pandas_stub = sys.modules["pandas"]
if not hasattr(pandas_stub, "read_csv"):

    class DataFrame:
        def __init__(self, rows):
            self._rows = rows

        def to_csv(self, path, mode="w", header=True, index=False):
            exists = os.path.exists(path)
            with open(path, mode, newline="") as f:
                names = self._rows[0].keys() if self._rows else []
                writer = csv.DictWriter(f, fieldnames=names)
                if header and not exists:
                    writer.writeheader()
                for row in self._rows:
                    writer.writerow(row)

        def get(self, key, default=None):
            if self._rows and key in self._rows[0]:
                return Series([row.get(key) for row in self._rows])
            return default

        @property
        def iloc(self):
            df = self

            class _ILoc:
                def __getitem__(self, idx):
                    return df._rows[idx]

            return _ILoc()

        def __len__(self):
            return len(self._rows)

    def read_csv(path):
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                parsed = {}
                for k, v in row.items():
                    try:
                        parsed[k] = float(v)
                    except (ValueError, TypeError):
                        parsed[k] = v
                rows.append(parsed)
        return DataFrame(rows)

    class Series(list):
        def sum(self):
            return sum(x for x in self if isinstance(x, (int, float)))

    pandas_stub.DataFrame = DataFrame
    pandas_stub.read_csv = read_csv
    pandas_stub.Series = Series

prom_stub = sys.modules["prometheus_client"]
if not hasattr(prom_stub, "CollectorRegistry"):

    class CollectorRegistry:
        pass

    class _Metric:
        class _Value:
            def __init__(self, v: float = 0.0):
                self._v = v

            def get(self) -> float:
                return self._v

            def set(self, v: float) -> None:
                self._v = v

        def __init__(self, *a, **k) -> None:
            self._value = self._Value()

        def inc(self, amt: float = 1.0) -> None:
            self._value.set(self._value.get() + amt)

        def set(self, v: float) -> None:
            self._value.set(v)

        def observe(self, v: float) -> None:
            self.inc(v)

    Counter = Gauge = Histogram = _Metric

    def start_http_server(*a, **k):
        pass

    prom_stub.CollectorRegistry = CollectorRegistry
    prom_stub.Counter = Counter
    prom_stub.Gauge = Gauge
    prom_stub.Histogram = Histogram
    prom_stub.start_http_server = start_http_server


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


@pytest.fixture(autouse=True)
def _mock_wait_ready(monkeypatch):
    import atlasbot.market_data as md

    monkeypatch.setattr(md.MarketData, "wait_ready", lambda self, timeout=15: True)
    monkeypatch.setattr(
        md.MarketData, "latest_trade", lambda self, sym: 100.0, raising=False
    )
    yield


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for pkg in ("pandas", "requests", "ccxt"):
    if not pkg_resources.working_set.by_key.get(pkg):
        dist = pkg_resources.Distribution(project_name=pkg, version="0.0")
        pkg_resources.working_set.add(dist)

os.environ.setdefault("ATLAS_TEST", "1")
