import threading
import pytest

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
            return {"price": "100"}

    return Resp()


def test_rest_fallback(monkeypatch):
    monkeypatch.setattr(md, "REST_POLL_INTERVAL", 0.01)
    monkeypatch.setattr(md, "SEED_TIMEOUT", 0.0)
    monkeypatch.setattr(md.websocket, "WebSocketApp", lambda *a, **k: FakeWS())
    import requests
    monkeypatch.setattr(requests, "get", fake_get)

    market = md.get_market(SYMBOLS)
    assert market.wait_ready(2)
    assert market.mode == "rest"
    for sym in SYMBOLS:
        assert market.latest_trade(sym) == 100.0

