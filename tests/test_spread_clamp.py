from atlasbot.market_data import _SPREAD, get_spread_bps


def test_spread_clamp():
    _SPREAD["XYZ"] = 0.2
    assert get_spread_bps("XYZ") == 1
    _SPREAD["XYZ"] = 30
    assert get_spread_bps("XYZ") == 15
