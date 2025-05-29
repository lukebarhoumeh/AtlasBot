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

    def next_advice(self, symbol: str):
        return self._advice


def _setup_bot(monkeypatch, advice):
    monkeypatch.setattr(tr, "SYMBOLS", ["BTC-USD"])
    monkeypatch.setattr(cfg, "SYMBOLS", ["BTC-USD"])
    monkeypatch.setattr(tr, "fetch_price", lambda s: 100.0)
    monkeypatch.setattr(tr, "calculate_atr", lambda s: 1.0)
    monkeypatch.setattr(tr.risk, "check_risk", lambda order: True)
    dummy = DummyExec()
    monkeypatch.setattr(tr, "get_backend", lambda name=None: dummy)
    bot = tr.IntradayTrader(decision_engine=DummyEngine(advice), backend="sim")
    return bot, dummy


def test_flat_bias(monkeypatch):
    advice = {
        "bias": "flat",
        "edge": 0.0,
        "confidence": 0.0,
        "rationale": {"orderflow": 0.0, "momentum": 0.0, "macro": 0.0},
    }
    bot, dummy = _setup_bot(monkeypatch, advice)
    bot.run_cycle()
    assert not dummy.calls


def test_conflict_filter(monkeypatch):
    advice = {
        "bias": "long",
        "edge": 0.05,
        "confidence": 1.0,
        "rationale": {"orderflow": -0.5, "momentum": 0.5, "macro": 0.0},
    }
    bot, dummy = _setup_bot(monkeypatch, advice)
    for _ in range(3):
        bot.run_cycle()
    assert not dummy.calls
