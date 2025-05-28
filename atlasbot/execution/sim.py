import time
from atlasbot.utils import fetch_price


def submit_order(side: str, size_usd: float, symbol: str) -> str:
    """Simulated immediate fill at current market price."""
    price = fetch_price(symbol)
    qty = size_usd / price
    # id is timestamp string
    exec_id = f"sim-{time.time()}"
    return exec_id, qty, price
