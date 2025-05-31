import pytest

from atlasbot.execution_engine import fill_probability


def test_fill_probability():
    prob = fill_probability(20, 2)
    assert prob == pytest.approx(min(1.0, 0.6 * (20 / 2) ** 1.3))
