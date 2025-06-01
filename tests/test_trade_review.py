import pandas as pd

from atlasbot.trade_review import summarize


def test_summarize(tmp_path):
    path = tmp_path / "pnl.csv"
    df = pd.DataFrame(
        [
            {"realised": 1.0, "mtm": 0.0, "latency_ms": 10.0},
            {"realised": -2.0, "mtm": 0.0, "latency_ms": 20.0},
        ]
    )
    df.to_csv(path, index=False)
    stats = summarize(str(path))
    assert stats["trades"] == 2
    assert stats["win_rate"] == 0.5
    assert stats["max_drawdown"] <= 0.0
    assert stats["avg_latency_ms"] == 15.0
