import time
import random
from atlasbot.utils import fetch_price
from atlasbot.config import SLIP_PCT_STD
from .base import log_fill


def submit_order(side: str, size_usd: float, symbol: str) -> str:
    """Simulated immediate fill at current market price."""
    price = fetch_price(symbol)
    slip_pct = random.gauss(0, SLIP_PCT_STD)
    fill_price = price * (1 + slip_pct)
    qty = size_usd / fill_price
    exec_id = f"sim-{time.time()}"
    log_fill(symbol, side, size_usd, fill_price, size_usd * slip_pct)
    return exec_id, qty, fill_price
