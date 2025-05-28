import importlib

import atlasbot.risk as risk_mod


def test_portfolio_snapshot(monkeypatch):
    risk = importlib.reload(risk_mod)
    monkeypatch.setattr(risk, "fetch_price", lambda s: 100.0)
    risk.record_fill("BTC-USD", "buy", 100, 100, 0.1, 0.2)
    monkeypatch.setattr(risk, "fetch_price", lambda s: 105.0)
    snap = risk.portfolio_snapshot()
    assert set(snap.keys()) >= {
        "timestamp",
        "equity_usd",
        "cash_usd",
        "unreal_mtm_usd",
        "fees_usd",
        "slippage_usd",
        "per_symbol",
    }
    assert "BTC-USD" in snap["per_symbol"]
    ps = snap["per_symbol"]["BTC-USD"]
    assert ps["pos"] == 1.0
    assert ps["mtm"] == 5.0
    assert snap["fees_usd"] == 0.1
    assert snap["slippage_usd"] == 0.2
