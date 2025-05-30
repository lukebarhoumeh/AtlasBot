import atlasbot.config as cfg
import atlasbot.trader as tr


class DummyExec:
    def __init__(self):
        self.calls = []

    def submit_order(self, side: str, size_usd: float, symbol: str):
        self.calls.append((side, size_usd, symbol))


class DummyEngine:
    def __init__(self, advice):
        self._advice = advice

    def next_advice(self, _symbol: str):
        return self._advice


def _setup(monkeypatch, advice):
    monkeypatch.setattr(tr, "SYMBOLS", ["BTC-USD"])
    monkeypatch.setattr(cfg, "SYMBOLS", ["BTC-USD"])
    monkeypatch.setattr(tr, "fetch_price", lambda s: 100.0)
    monkeypatch.setattr(tr, "calculate_atr", lambda s: 1.0)
    monkeypatch.setattr(tr.risk, "check_risk", lambda order: True)
    dummy = DummyExec()
    monkeypatch.setattr(tr, "get_backend", lambda name=None: dummy)
    bot = tr.IntradayTrader(decision_engine=DummyEngine(advice), backend="sim")
    return bot, dummy


def test_edge_threshold_env(monkeypatch):
    monkeypatch.setattr(cfg, "MIN_EDGE_BPS", 80, raising=False)
    advice = {
        "bias": "long",
        "edge": 0.002,
        "confidence": 1.0,
        "rationale": {"orderflow": 0.5, "momentum": 0.5, "macro": 0.0},
    }
    bot, dummy = _setup(monkeypatch, advice)
    bot.run_cycle()
    assert not dummy.calls


def test_conflict_thresh_env(monkeypatch):
    monkeypatch.setattr(cfg, "CONFLICT_THRESH", 0.6, raising=False)
    advice = {
        "bias": "long",
        "edge": 0.05,
        "confidence": 1.0,
        "rationale": {"orderflow": -0.5, "momentum": 0.5, "macro": 0.0},
    }
    bot, dummy = _setup(monkeypatch, advice)
    bot.run_cycle()
    assert dummy.calls


def test_dynamic_size_curb(monkeypatch):
    advice = {
        "bias": "long",
        "edge": 0.05,
        "confidence": 1.0,
        "rationale": {"orderflow": 0.2, "momentum": 0.3, "macro": 0.0},
    }
    bot, dummy = _setup(monkeypatch, advice)
    monkeypatch.setattr(tr.risk, "equity", lambda: 1000.0)
    monkeypatch.setattr(tr.risk, "trade_count_day", lambda: 101)
    bot.run_cycle()
    assert dummy.calls
    _, size_usd, _ = dummy.calls[0]
    base = 1000.0 * cfg.RISK_PER_TRADE * 1.0 / (1.0 / 100.0)
    assert size_usd == base * 0.75
