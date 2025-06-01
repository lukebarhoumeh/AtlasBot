import random
import time
from typing import List, Tuple

from atlasbot.config import SLIPPAGE_BPS
from atlasbot.utils import fetch_price

from .base import Fill, log_fill


def _sim_book(price: float) -> List[Tuple[float, float]]:
    """Return a fake order book around *price*."""

    levels = []
    for i in range(1, 6):
        levels.append((price * (1 - i * 0.0005), 1.0))
    for i in range(1, 6):
        levels.append((price * (1 + i * 0.0005), 1.0))
    return levels


def submit_order(side: str, size_usd: float, symbol: str) -> Fill:
    """Simulated immediate fill with slippage and latency."""

    price = fetch_price(symbol)
    book = _sim_book(price)
    slip_pct = random.gauss(0, SLIPPAGE_BPS / 10_000)
    fill_price = price * (1 + slip_pct if side == "buy" else 1 - slip_pct)
    qty = size_usd / fill_price
    exec_id = f"sim-{time.time()}"
    log_fill(
        symbol,
        side,
        size_usd,
        fill_price,
        size_usd * slip_pct,
        book_before=book,
        book_after=book,
        latency_ms=0.0,
    )
    return Fill(exec_id, qty, fill_price)


def submit_maker_order(side: str, size_usd: float, symbol: str) -> Fill | None:
    """Attempt maker order with probabilistic fill."""

    price = fetch_price(symbol)
    book = _sim_book(price)
    prob = 0.7
    if random.random() < prob:
        qty = size_usd / price
        exec_id = f"maker-{time.time()}"
        log_fill(
            symbol,
            side,
            size_usd,
            price,
            0.0,
            maker=True,
            book_before=book,
            book_after=book,
            latency_ms=0.0,
        )
        return Fill(exec_id, qty, price)
    return None
