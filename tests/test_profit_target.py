import atlasbot.config as cfg


def test_profit_target_edge():
    for sym in cfg.SYMBOLS:
        pt = cfg.profit_target(sym)
        assert pt > cfg.TAKER_FEE + cfg.SLIPPAGE_BPS / 10_000
