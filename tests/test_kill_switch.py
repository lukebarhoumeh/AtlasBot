import importlib

import atlasbot.risk as risk_mod


def test_kill_switch(monkeypatch):
    risk = importlib.reload(risk_mod)
    monkeypatch.setattr(risk, "fetch_price", lambda s: 100.0)
    risk._risk.cash = 100.0
    risk._risk.equity = 100.0
    risk._risk.day_high_equity = 100.0
    # trade causing >5% drawdown
    risk.record_fill("BTC-USD", "buy", 10, 100, 0.0, 0.0)
    assert risk.kill_switch_triggered()
