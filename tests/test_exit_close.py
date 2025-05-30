import importlib

import atlasbot.trader as tr_mod
from atlasbot.execution.base import Fill


class DummyExec:
    def __init__(self) -> None:
        self.calls = []

    def submit_order(self, side: str, size_usd: float, symbol: str):
        self.calls.append((side, size_usd, symbol))
        return Fill("id", size_usd / 100.0, 100.0)


def test_exit_close_tp(monkeypatch):
    tr = importlib.reload(tr_mod)
    bot = tr.IntradayTrader(backend="sim")
    bot.exec = DummyExec()
    prices = [100.0, 103.0]
    monkeypatch.setattr(tr, "fetch_price", lambda s: prices.pop(0))
    monkeypatch.setattr(tr.time, "sleep", lambda s: None)
    before = tr.metrics.exit_tp_total._value.get()
    bot._exit_position("BTC-USD", "buy", 1.0, 100.0, 1.0)
    after = tr.metrics.exit_tp_total._value.get()
    assert after == before + 1
    assert bot.exec.calls
