from atlasbot import decision_engine
from atlasbot.decision_engine import expected_edge_bps


def test_edge_low_hurdle(monkeypatch):
    monkeypatch.setattr(decision_engine, "vol_window_std", lambda: 0.001575)
    edge = expected_edge_bps(0.8, mid=0.45, spread_bps=5)
    assert edge >= 5
