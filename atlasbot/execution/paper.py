import os
import time
from typing import Any

import requests

from atlasbot.utils import fetch_price

from .base import Fill, log_fill


def submit_order(side: str, size_usd: float, symbol: str) -> Fill:
    """Send order to Coinbase paper API or fall back to instant fill."""
    api_key = os.getenv("COINBASE_PAPER_KEY")
    endpoint = "https://api.coinbase.com/api/v3/brokerage/orders"  # paper
    if not api_key:
        price = fetch_price(symbol)
        qty = size_usd / price
        log_fill(symbol, side, size_usd, price, 0.0)
        return Fill("paper-sim", qty, price)

    payload = {
        "side": side,
        "client_order_id": f"paper-{int(time.time())}",
        "product_id": symbol,
        "size": str(size_usd / fetch_price(symbol)),
        "type": "market",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    for attempt in range(3):
        try:
            r = requests.post(endpoint, json=payload, headers=headers, timeout=5)
            if r.status_code == 429 or 400 <= r.status_code < 500:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
            data: dict[str, Any] = r.json()
            order_id = data.get("order_id", "paper-unknown")
            price = float(data.get("average_filled_price", fetch_price(symbol)))
            qty = float(data.get("filled_size", 0))
            log_fill(symbol, side, qty * price, price, 0.0)
            return Fill(order_id, qty, price)
        except Exception:
            time.sleep(2**attempt)
    price = fetch_price(symbol)
    qty = size_usd / price
    log_fill(symbol, side, size_usd, price, 0.0)
    return Fill("paper-error", qty, price)


def submit_maker_order(side: str, size_usd: float, symbol: str) -> Fill | None:
    """Maker order via paper API, return None if not filled."""
    api_key = os.getenv("COINBASE_PAPER_KEY")
    if not api_key:
        return None
    endpoint = "https://api.coinbase.com/api/v3/brokerage/orders"  # paper
    payload = {
        "side": side,
        "client_order_id": f"maker-{int(time.time())}",
        "product_id": symbol,
        "size": str(size_usd / fetch_price(symbol)),
        "type": "limit",
        "post_only": True,
        "limit_price": str(fetch_price(symbol)),
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.post(endpoint, json=payload, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        if not data.get("success", True):
            return None
        order_id = data.get("order_id", f"maker-{int(time.time())}")
        price = float(data.get("average_filled_price", fetch_price(symbol)))
        qty = float(data.get("filled_size", 0))
        if qty:
            log_fill(symbol, side, qty * price, price, 0.0, maker=True)
            return Fill(order_id, qty, price)
    except Exception:
        pass
    return None
