import os

import atlasbot.execution.base as base
import atlasbot.risk as risk


def test_pnl_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(base, "PNL_PATH", tmp_path / "pnl.csv")
    monkeypatch.setattr(risk, "SUMMARY_PATH", tmp_path / "summary.jsonl")
    monkeypatch.setattr(risk, "fetch_price", lambda s: 100.0)
    base.log_fill("BTC-USD", "buy", 100, 100, 0.0)
    risk._risk._last_snapshot -= risk.timedelta(minutes=5)
    risk.snapshot()
    assert os.path.exists(base.PNL_PATH)
    assert os.path.exists(risk.SUMMARY_PATH)
    assert len(open(risk.SUMMARY_PATH).read().splitlines()) >= 1
