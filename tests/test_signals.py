import importlib
import atlasbot.signals.orderflow as of
mom = importlib.import_module("atlasbot.signals.momentum")
from collections import deque

class FakeMarket:
    def minute_bars(self, _):
        return deque([(1,2,0,1)]*20)

def test_imbalance_range(monkeypatch):
    monkeypatch.setattr(of, "_orderflow", of.OrderFlow([]))
    assert -1.0 <= of.imbalance("BTC-USD") <= 1.0

def test_momentum(monkeypatch):
    monkeypatch.setattr(mom, "get_market", lambda: FakeMarket())
    val = mom.momentum("BTC-USD")
    assert -1.0 <= val <= 1.0
