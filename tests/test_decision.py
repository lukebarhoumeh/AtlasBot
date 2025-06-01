import pytest

from atlasbot import decision_engine
from atlasbot.decision_engine import expected_edge_bps


def test_expected_edge(monkeypatch):
    monkeypatch.setattr(decision_engine, "vol_window_std", lambda: 0.01)
    edge = expected_edge_bps(0.5, 1.0, spread_bps=5)
    assert edge == pytest.approx(1e4 * 0.5 * 0.01 / 1.0 - (0 + 4 + 0.2 * 5))
