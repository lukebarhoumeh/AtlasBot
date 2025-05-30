import importlib
from datetime import datetime, timezone

import pandas as pd

import atlasbot.run_logger as rl_mod


def test_csv_writer(monkeypatch, tmp_path):
    rl = importlib.reload(rl_mod)
    monkeypatch.setattr(rl, "RUN_DIR", tmp_path)
    rl.RUN_CSV = tmp_path / f"ledger_{datetime.now(timezone.utc):%H%M%S}.csv"
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": "BTC-USD",
        "side": "buy",
        "notional": 100.0,
        "price": 100.0,
        "fee": 0.1,
        "slip": 0.0,
        "realised": 0.0,
        "mtm": 0.0,
    }
    rl.append(row)
    rl.append(row)
    df = pd.read_csv(rl.RUN_CSV)
    assert len(df) == 2
    assert df.iloc[0]["symbol"] == "BTC-USD"
