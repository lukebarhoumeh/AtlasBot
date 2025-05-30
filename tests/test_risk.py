from atlasbot import risk


def test_limits():
    order = {"symbol": "BTC-USD", "side": "buy", "size_usd": 500}
    assert risk.check_risk(order)
    risk.record_fill("BTC-USD", "buy", 500, 100, 0.0, 0.0)
    order = {"symbol": "BTC-USD", "side": "buy", "size_usd": 600}
    assert not risk.check_risk(order)
    risk.record_fill("BTC-USD", "sell", 500, 100, 0.0, 0.0)
