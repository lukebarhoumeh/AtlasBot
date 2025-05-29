import importlib

import atlasbot.metrics as metrics_mod


class DummyMarket:
    def __init__(self):
        self._symbols = ["BTC-USD"]

    def feed_latency(self):
        return 130.0


def test_watchdog(monkeypatch):
    metrics = importlib.reload(metrics_mod)
    dummy = DummyMarket()
    monkeypatch.setattr(metrics, "get_market", lambda: dummy)

    def fake_get(url, timeout=5):
        class Resp:
            ok = True

            def json(self):
                return {"price": "101"}

        return Resp()

    monkeypatch.setattr(metrics.requests, "get", fake_get)
    before = metrics.feed_watchdog_total._value.get()
    metrics.feed_watchdog_check()
    after = metrics.feed_watchdog_total._value.get()
    assert after == before + 1
