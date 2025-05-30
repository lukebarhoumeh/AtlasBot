import os

import pytest

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
