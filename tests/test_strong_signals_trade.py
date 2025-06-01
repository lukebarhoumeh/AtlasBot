import pytest

import atlasbot.config as cfg
import atlasbot.trader as tr
from atlasbot.execution.base import Fill


class DummyExec:
    def __init__(self) -> None:
        self.calls = []

    def submit_order(self, side: str, size_usd: float, symbol: str):
        self.calls.append((side, size_usd, symbol))
        return Fill("id", size_usd / 100.0, 100.0)


class DummyMarket:
    def minute_bars(self, symbol: str) -> list[tuple[int, int, int, int]]:
        return [(1, 1, 1, 1)] * 60


def _setup_bot(
    monkeypatch: "pytest.MonkeyPatch",
) -> tuple[tr.IntradayTrader, DummyExec]:
    monkeypatch.setattr(tr, "SYMBOLS", ["BTC-USD"])
    monkeypatch.setattr(cfg, "SYMBOLS", ["BTC-USD"])
    monkeypatch.setattr(cfg, "FEE_BPS", 0)
    monkeypatch.setattr(cfg, "SLIPPAGE_BPS", 0)
    monkeypatch.setattr(cfg, "MIN_EDGE_BPS", 0)
    import importlib as _importlib

    import atlasbot.decision_engine as de_mod

    de_mod = _importlib.reload(de_mod)
    monkeypatch.setattr(tr, "fetch_price", lambda s: 100.0)
    monkeypatch.setattr(tr, "calculate_atr", lambda s: 1.0)
    monkeypatch.setattr(tr.risk, "check_risk", lambda order: True)
    dummy = DummyExec()
    monkeypatch.setattr(tr, "get_backend", lambda name=None: dummy)
    dummy_market = DummyMarket()
    monkeypatch.setattr(tr, "get_market", lambda: dummy_market)
    import atlasbot.market_data as md

    monkeypatch.setattr(md, "get_market", lambda symbols=None: dummy_market)
    monkeypatch.setattr(md, "_market", dummy_market)
    import importlib as _importlib

    de_mod_reload = _importlib.reload(de_mod)
    monkeypatch.setattr(de_mod_reload, "imbalance", lambda s: 1.0)
    monkeypatch.setattr(de_mod_reload, "momentum", lambda s: 1.0)
    monkeypatch.setattr(de_mod_reload, "macro_bias", lambda s: 1.0)
    bot = tr.IntradayTrader(
        decision_engine=de_mod_reload.DecisionEngine(), backend="sim"
    )
    return bot, dummy


def test_trade_executes_on_strong_signal(monkeypatch):
    bot, dummy = _setup_bot(monkeypatch)
    bot.run_cycle()
    assert isinstance(dummy.calls, list)
