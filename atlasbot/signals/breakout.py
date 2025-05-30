from typing import Deque

from atlasbot.market_data import get_market

WINDOW = 20


def breakout(symbol: str) -> float:
    """Return 1 for long breakout, -1 for short breakout, else 0."""
    bars: Deque[tuple[float, float, float, float]] = get_market().minute_bars(symbol)
    if len(bars) <= WINDOW:
        return 0.0
    recent = list(bars)[-WINDOW - 1 :]
    prev = [b[3] for b in recent[:-1]]
    last = recent[-1][3]
    if not prev:
        return 0.0
    if last > max(prev):
        return 1.0
    if last < min(prev):
        return -1.0
    return 0.0
