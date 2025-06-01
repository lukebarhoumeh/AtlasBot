import importlib

import atlasbot.config as cfg_mod
import atlasbot.trader as tr_mod
from atlasbot.execution.base import Fill


class DummyExec:
    def __init__(self):
        self.maker = 0
        self.taker = 0

    def submit_maker_order(self, side: str, size_usd: float, symbol: str):
        self.maker += 1
        return Fill("id", 1.0, 100.0)

    def submit_order(self, side: str, size_usd: float, symbol: str):
        self.taker += 1
        return Fill("id", 1.0, 100.0)


class DummyMarket:
    def minute_bars(self, symbol):
        return [(1, 1, 1, 1)] * 60


def _run_bot(monkeypatch, mode: str) -> DummyExec:
    monkeypatch.setenv("EXECUTION_MODE", mode)
    cfg = importlib.reload(cfg_mod)
    tr = importlib.reload(tr_mod)
    monkeypatch.setattr(cfg, "FEE_BPS", 0)
    monkeypatch.setattr(cfg, "SLIPPAGE_BPS", 0)
    monkeypatch.setattr(cfg, "MIN_EDGE_BPS", 0)
    import importlib as _importlib

    import atlasbot.decision_engine as de

    de = _importlib.reload(de)
    monkeypatch.setattr(tr, "SYMBOLS", ["BTC-USD"])
    monkeypatch.setattr(cfg, "SYMBOLS", ["BTC-USD"])
    monkeypatch.setattr(tr, "fetch_price", lambda s: 100.0)
    monkeypatch.setattr(tr, "calculate_atr", lambda s: 1.0)
    monkeypatch.setattr(tr.risk, "check_risk", lambda order: True)
    dummy = DummyExec()
    monkeypatch.setattr(tr, "get_backend", lambda name=None: dummy)
    monkeypatch.setattr(tr.IntradayTrader, "_exit_position", lambda *a, **k: None)
    dummy_market = DummyMarket()
    monkeypatch.setattr(tr, "get_market", lambda: dummy_market)
    import atlasbot.market_data as md

    monkeypatch.setattr(md, "get_market", lambda symbols=None: dummy_market)
    monkeypatch.setattr(md, "_market", dummy_market)
    monkeypatch.setattr(de, "imbalance", lambda s: 1.0)
    monkeypatch.setattr(de, "momentum", lambda s: 1.0)
    monkeypatch.setattr(de, "macro_bias", lambda s: 1.0)
    bot = tr.IntradayTrader(decision_engine=de.DecisionEngine(), backend="sim")
    bot.run_cycle()
    return dummy


def test_env_exec_mode(monkeypatch):
    dummy = _run_bot(monkeypatch, "maker")
    assert dummy.maker >= 0
    dummy = _run_bot(monkeypatch, "taker")
    assert dummy.taker >= 0
