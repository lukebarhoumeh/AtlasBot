import os

import pandas as pd

import atlasbot.execution.base as base
import atlasbot.execution.sim as sim

PNL_PATH = base.PNL_PATH


def test_pnl_row(monkeypatch, tmp_path):
    monkeypatch.setattr(sim, "fetch_price", lambda s: 100.0)
    monkeypatch.setattr(sim.random, "gauss", lambda m, s: 0.0)
    monkeypatch.setattr(base, "PNL_PATH", tmp_path / "pnl.csv")
    global PNL_PATH
    PNL_PATH = base.PNL_PATH
    if os.path.exists(PNL_PATH):
        os.remove(PNL_PATH)
    sim.submit_order("buy", 100, "BTC-USD")
    sim.submit_order("sell", 50, "BTC-USD")
    df = pd.read_csv(PNL_PATH)
    row = df.iloc[-1]
    assert len(row) == 13
    assert row["fee"] >= 0
    assert row["slip"] >= 0
