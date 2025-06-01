from __future__ import annotations

import time

from atlasbot.config import CURRENT_TAKER_BPS
from atlasbot.execution.base import Fill


def fill_probability(edge_bps: float, spread_bps: float) -> float:
    """Return expected fill probability for a maker order."""
    if spread_bps <= 0:
        return 0.0
    return min(1.0, 0.6 * (edge_bps / spread_bps) ** 1.3)


def place_maker(
    exec_api: object,
    side: str,
    size_usd: float,
    symbol: str,
    edge_bps: float,
    spread_bps: float,
) -> Fill | None:
    """Place maker-first order with timed fallback to taker."""
    filled = None
    if hasattr(exec_api, "submit_maker_order"):
        filled = exec_api.submit_maker_order(side, size_usd, symbol)
        if filled:
            return filled
        wait_s = max(2.0, 1.0 / max(fill_probability(edge_bps, spread_bps), 1e-6))
        time.sleep(wait_s)
    if edge_bps > CURRENT_TAKER_BPS:
        return exec_api.submit_order(side, size_usd, symbol)
    return None
