import importlib

import atlasbot.diagnostics as diagnostics


def test_record_and_fetch_rejects():
    diag = importlib.reload(diagnostics)
    diag.record_reject("edge", "below threshold", 4.0, symbol="BTC-USD")
    diag.record_reject("edge", "below threshold", 3.0, symbol="ETH-USD")
    rec = diag.last_rejects("edge", 1)[0]
    assert rec["edge_bps"] == 3.0
    assert rec["symbol"] == "ETH-USD"


def test_env_config(monkeypatch):
    diag = importlib.reload(diagnostics)
    monkeypatch.setenv("PAPER_CASH", "9999")
    info = diag.get_env_config()
    assert info["env"]["PAPER_CASH"] == "9999"
    assert "MAX_NOTIONAL" in info["config"]


def test_summary_csv():
    diag = importlib.reload(diagnostics)
    diag.record_reject("risk", "limit", 10.0, symbol="BTC-USD")
    out = diag.summary_csv(5)
    assert "BTC-USD" in out
    assert "CONFIG" in out
