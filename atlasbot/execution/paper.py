from atlasbot.utils import fetch_price
from .base import log_fill


def submit_order(side: str, size_usd: float, symbol: str) -> str:
    """Placeholder for Coinbase Advanced Trade paper API."""
    # TODO: integrate real API calls
    price = fetch_price(symbol)
    qty = size_usd / price
    log_fill(symbol, side, size_usd, price, 0.0)
    return "paper-0", qty, price
