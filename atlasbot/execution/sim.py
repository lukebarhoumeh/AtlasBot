import random
import time

from atlasbot.config import SLIPPAGE_BPS
from atlasbot.utils import fetch_price

from .base import Fill, log_fill


def submit_order(side: str, size_usd: float, symbol: str) -> Fill:
    """Simulated immediate fill at current market price."""
    price = fetch_price(symbol)
    slip_pct = random.gauss(0, SLIPPAGE_BPS / 10_000)
    fill_price = price * (1 + slip_pct)
    qty = size_usd / fill_price
    exec_id = f"sim-{time.time()}"
    log_fill(symbol, side, size_usd, fill_price, size_usd * slip_pct)
    return Fill(exec_id, qty, fill_price)


def submit_maker_order(side: str, size_usd: float, symbol: str) -> Fill | None:
    """Attempt maker order; 50% chance to fill."""
    if random.random() < 0.5:
        price = fetch_price(symbol)
        qty = size_usd / price
        exec_id = f"maker-{time.time()}"
        log_fill(symbol, side, size_usd, price, 0.0, maker=True)
        return Fill(exec_id, qty, price)
    return None
