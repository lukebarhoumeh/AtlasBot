import atlasbot.market_data as md
from atlasbot.config import SYMBOLS


class FakeWS:
    def run_forever(self, *a, **k):
        raise md.websocket._exceptions.WebSocketBadStatusException("err", 403)

    def close(self):
        pass


def fake_get(url, timeout=5):
    class Resp:
        ok = True

        def json(self):
            if "candles" in url:
                return [[0, 1, 2, 3, 4, 0]] * 150
            return {"price": "100"}

    return Resp()


def test_market_instance_resets(monkeypatch):
    monkeypatch.setattr(md, "SEED_TIMEOUT", 0)
    monkeypatch.setattr(md.websocket, "WebSocketApp", lambda *a, **k: FakeWS())
    import requests

    monkeypatch.setattr(requests, "get", fake_get)
    md._market = None
    m1 = md.get_market(SYMBOLS)
    assert m1.wait_ready(1)
    md._market = None
    m2 = md.get_market(SYMBOLS)
    assert m2 is not m1
    assert m2.wait_ready(1)
    for sym in SYMBOLS:
        assert m2.latest_trade(sym) == 100.0
