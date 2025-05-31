import importlib

import atlasbot.execution.base as base


class DummyExec:
    def __init__(self) -> None:
        self.taker = 0
        self.maker = 0

    def submit_maker_order(self, side: str, size_usd: float, symbol: str):
        self.maker += 1
        return None

    def submit_order(self, side: str, size_usd: float, symbol: str):
        self.taker += 1
        return base.Fill("id", size_usd / 100, 100.0)


def test_maker_fallthrough(monkeypatch):
    base_mod = importlib.reload(base)
    dummy = DummyExec()
    base_mod.maker_to_taker(dummy, "buy", 100.0, "BTC-USD", wait_s=0)
    assert dummy.maker == 1
    assert dummy.taker == 1
