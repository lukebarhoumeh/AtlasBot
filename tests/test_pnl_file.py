import os
import pandas as pd
import atlasbot.execution.sim as sim
from atlasbot.execution.base import PNL_PATH


def test_pnl_row(monkeypatch, tmp_path):
    monkeypatch.setattr(sim, "fetch_price", lambda s: 100.0)
    monkeypatch.setattr(sim.random, "gauss", lambda m, s: 0.0)
    if os.path.exists(PNL_PATH):
        os.remove(PNL_PATH)
    sim.submit_order("buy", 100, "BTC-USD")
    sim.submit_order("sell", 50, "BTC-USD")
    df = pd.read_csv(PNL_PATH)
    row = df.iloc[-1]
    assert len(row) == 9
    assert row["fee"] >= 0
    assert row["slip"] >= 0

