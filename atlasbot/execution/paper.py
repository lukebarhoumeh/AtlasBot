import os
import time
import requests
from atlasbot.utils import fetch_price
from .base import log_fill


def submit_order(side: str, size_usd: float, symbol: str) -> str:
    """Send order to Coinbase paper API or fall back to instant fill."""
    api_key = os.getenv("COINBASE_PAPER_KEY")
    endpoint = "https://api.coinbase.com/api/v3/brokerage/orders"  # paper
    if not api_key:
        price = fetch_price(symbol)
        qty = size_usd / price
        log_fill(symbol, side, size_usd, price, 0.0)
        return "paper-sim", qty, price

    payload = {
        "side": side,
        "client_order_id": f"paper-{int(time.time())}",
        "product_id": symbol,
        "size": str(size_usd / fetch_price(symbol)),
        "type": "market",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.post(endpoint, json=payload, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        order_id = data.get("order_id", "paper-unknown")
        price = float(data.get("average_filled_price", fetch_price(symbol)))
        qty = float(data.get("filled_size", 0))
        log_fill(symbol, side, qty * price, price, 0.0)
        return order_id, qty, price
    except Exception:
        price = fetch_price(symbol)
        qty = size_usd / price
        log_fill(symbol, side, size_usd, price, 0.0)
        return "paper-error", qty, price
