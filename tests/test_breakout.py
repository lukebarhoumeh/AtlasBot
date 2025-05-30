import importlib
from collections import deque

bo = importlib.import_module("atlasbot.signals.breakout")


class FakeMarket:
    def __init__(self, bars):
        self._bars = {"BTC-USD": deque(bars, maxlen=25)}

    def minute_bars(self, sym):
        return self._bars[sym]


def test_breakout_signal(monkeypatch):
    bars = [(i, i, i, i) for i in range(1, 22)]
    monkeypatch.setattr(bo, "get_market", lambda symbols=None: FakeMarket(bars))
    assert bo.breakout("BTC-USD") == 1

    down = [(i, i, i, i) for i in range(22, 0, -1)]
    monkeypatch.setattr(bo, "get_market", lambda symbols=None: FakeMarket(down))
    assert bo.breakout("BTC-USD") == -1
