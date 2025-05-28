from atlasbot import risk


def test_limits():
    order = {"symbol": "BTC-USD", "side": "buy", "size_usd": 500}
    assert risk.check_risk(order)
    risk.update_position("BTC-USD", 500)
    order = {"symbol": "BTC-USD", "side": "buy", "size_usd": 600}
    assert not risk.check_risk(order)
    risk.add_pnl(-200)
    order = {"symbol": "BTC-USD", "side": "sell", "size_usd": 100}
    assert not risk.check_risk(order)
