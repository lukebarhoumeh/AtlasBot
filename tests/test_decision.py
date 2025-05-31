import pytest

from atlasbot.decision_engine import expected_edge_bps


def test_expected_edge():
    edge = expected_edge_bps(0.5, 0.01, 1.0, fee_bps=10, slippage_bps=5)
    assert edge == pytest.approx(1e4 * (0.5 * 0.01 / 1.0) - 15)
