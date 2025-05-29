from typing import Deque

from atlasbot.market_data import get_market

WINDOW = 15  # bars


def _typical_price(bar: tuple[float, float, float, float]) -> float:
    o, h, low, c = bar
    return (o + h + low + c) / 4


def momentum(symbol: str) -> float:
    """Return normalised slope of approximate VWAP over last 15 bars."""
    bars: Deque[tuple[float, float, float, float]] = get_market().minute_bars(symbol)
    if len(bars) < WINDOW:
        return 0.0
    recent = list(bars)[-WINDOW:]
    prices = [_typical_price(b) for b in recent]
    slope = prices[-1] - prices[0]
    denom = max(prices) - min(prices)
    if denom == 0:
        return 0.0
    score = slope / denom
    return max(-1.0, min(1.0, score))
