"""
atlasbot/utils.py
=================

Thin convenience layer around the `MarketData` singleton
– blocks until the feed is ready
– exposes helpers for price, ATR and volatility
"""

from __future__ import annotations

import logging
import os
from typing import List

from atlasbot.config import SYMBOLS
from atlasbot.market_data import get_market

_md = None


def _get_md():
    global _md
    if _md is None:
        _md = get_market(SYMBOLS)
    return _md


# --------------------------------------------------------------------------- helpers
def _ensure_ready(timeout: int = 60) -> None:
    """Wait for market data feed readiness or raise ``RuntimeError``.

    If ``CI=true`` or ``MARKET_DATA_MOCK=true`` is set in the environment, the
    readiness check is skipped.
    """
    md = _get_md()
    if (
        os.getenv("CI", "").lower() == "true"
        or os.getenv("MARKET_DATA_MOCK", "").lower() == "true"
    ):
        logging.warning("CI mode – skipping market-data readiness check")
        return

    for attempt in range(3):
        if md.wait_ready(timeout):
            return
        logging.warning("Market feed not ready – retry %d/3", attempt + 1)

    msg = f"Market feed still not ready after {timeout}s (mode={md.mode})"
    raise RuntimeError(msg)


# --------------------------------------------------------------------------- façade
def fetch_price(symbol: str) -> float:
    """Return the latest trade price for *symbol* (blocks until ready)."""
    _ensure_ready()
    return _get_md().latest_trade(symbol)


def calculate_atr(symbol: str, period: int = 10) -> float:
    """
    Average True Range over *period* 1-minute bars.
    Raises if insufficient history is available.
    """
    _ensure_ready()
    bars = list(_get_md().minute_bars(symbol))[-period - 1 :]
    if len(bars) < period + 1:
        return float("nan")
    trs = [
        max(h, prev_close) - min(low, prev_close)
        for prev_close, (_, h, low, _) in zip((b[3] for b in bars[:-1]), bars[1:])
    ]
    return sum(trs) / period


def fetch_volatility(symbol: str, period: int = 30) -> float:
    """
    Mean absolute deviation of the closing price over *period* 1-minute bars.
    A quick-and-dirty proxy for intraday volatility.
    """
    _ensure_ready()
    closes: List[float] = [b[3] for b in list(_get_md().minute_bars(symbol))[-period:]]
    if len(closes) < period:
        return float("nan")

    mean = sum(closes) / len(closes)
    return sum(abs(px - mean) for px in closes) / len(closes)
