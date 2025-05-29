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
                return [[0,1,2,3,4,0]] * 150
            return {"price": "100"}
    return Resp()

def test_warm_start(monkeypatch):
    monkeypatch.setattr(md.websocket, "WebSocketApp", lambda *a, **k: FakeWS())
    monkeypatch.setattr(md, "SEED_TIMEOUT", 0)
    import requests
    monkeypatch.setattr(requests, "get", fake_get)
    md._market = None
    market = md.get_market(SYMBOLS)
    assert market.wait_ready(2)

