"""
atlasbot/utils.py
=================

Thin convenience layer around the `MarketData` singleton
– blocks until the feed is ready
– exposes helpers for price, ATR and volatility
"""

from __future__ import annotations

import time
from typing import List

from atlasbot.config import SYMBOLS
from atlasbot.market_data import get_market

# single global market-data object
_md = get_market(SYMBOLS)

# --------------------------------------------------------------------------- helpers
def _ensure_ready(timeout: int = 30) -> None:
    """
    Block until at least one symbol has a live price or `timeout` seconds pass.

    A longer default (30 s) avoids the “still not ready after 15 s” error loop
    you were seeing on slower or firewalled networks.
    """
    if not _md.wait_ready(timeout):
        raise RuntimeError(f"Market feed still not ready after {timeout}s")


# --------------------------------------------------------------------------- façade
def fetch_price(symbol: str) -> float:
    """Return the latest trade price for *symbol* (blocks until ready)."""
    _ensure_ready()
    return _md.latest_trade(symbol)


def calculate_atr(symbol: str, period: int = 14) -> float:
    """
    Average True Range over *period* 1-minute bars.
    Raises if insufficient history is available.
    """
    _ensure_ready()
    bars = list(_md.minute_bars(symbol))[-period - 1 :]
    if len(bars) < period + 1:
        raise RuntimeError(f"Need {period} bars for ATR")
    trs = [
        max(h, prev_close) - min(l, prev_close)
        for prev_close, (_, h, l, _) in zip((b[3] for b in bars[:-1]), bars[1:])
    ]
    return sum(trs) / period


def fetch_volatility(symbol: str, period: int = 60) -> float:
    """
    Mean absolute deviation of the closing price over *period* 1-minute bars.
    A quick-and-dirty proxy for intraday volatility.
    """
    _ensure_ready()
    closes: List[float] = [b[3] for b in list(_md.minute_bars(symbol))[-period:]]
    if len(closes) < period:
        raise RuntimeError(f"Need {period} closes for volatility")

    mean = sum(closes) / len(closes)
    return sum(abs(px - mean) for px in closes) / len(closes)
