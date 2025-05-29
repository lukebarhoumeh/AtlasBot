import importlib
import os
from datetime import datetime, timezone

import atlasbot.execution.base as base_mod
import atlasbot.risk as risk_mod


class FakeDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_ledger_snapshot(monkeypatch, tmp_path):
    risk = importlib.reload(risk_mod)
    base = importlib.reload(base_mod)
    monkeypatch.setattr(base, "PNL_PATH", tmp_path / "pnl.csv")
    monkeypatch.setattr(risk, "fetch_price", lambda s: 100.0)
    monkeypatch.setattr(risk, "datetime", FakeDatetime)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        base.log_fill("BTC-USD", "buy", 100, 100, 0.0)
        risk._risk._snapshot_ledger()
    finally:
        os.chdir(cwd)
    ledger = tmp_path / f"data/ledger_{FakeDatetime.now():%Y-%m-%d}.jsonl"
    assert ledger.exists()
    assert len(ledger.read_text().splitlines()) == 1
