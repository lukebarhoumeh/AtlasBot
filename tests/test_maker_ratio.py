import importlib

import pytest

import atlasbot.metrics as metrics_mod
import atlasbot.risk as risk_mod


class DummyMarket:
    def __init__(self):
        self._symbols = ["BTC-USD"]
        self.reconnects = 0

    def feed_latency(self):
        return 0

    def minute_bars(self, _):
        return [1]


def test_maker_ratio(monkeypatch):
    metrics = importlib.reload(metrics_mod)
    risk = importlib.reload(risk_mod)
    monkeypatch.setattr(metrics, "get_market", lambda: DummyMarket())
    monkeypatch.setattr(metrics, "feed_watchdog_check", lambda: None)
    monkeypatch.setattr(risk, "fetch_price", lambda s: 100.0)
    risk.record_fill("BTC-USD", "buy", 100, 100, 0.0, 0.0, maker=True)
    risk.record_fill("BTC-USD", "sell", 100, 100, 0.0, 0.0, maker=False)

    called = False

    def fake_sleep(_):
        nonlocal called
        called = True
        raise RuntimeError

    monkeypatch.setattr(metrics.time, "sleep", fake_sleep)
    with pytest.raises(RuntimeError):
        metrics._update_loop()
    assert called
    assert metrics.maker_ratio_g._value.get() == pytest.approx(0.5)
