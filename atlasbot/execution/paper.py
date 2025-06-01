import os
import random
import time
from typing import Any, List, Tuple

import requests

from atlasbot.utils import fetch_price

from .base import Fill, log_fill, request_with_retries


def _order_book(symbol: str, levels: int = 5) -> List[Tuple[float, float]]:
    """Return top *levels* of the order book as [(price, qty)]."""

    url = f"https://api.exchange.coinbase.com/products/{symbol}/book?level=2"
    try:
        resp = request_with_retries(requests.get, url)
        data = resp.json()
        bids = [(float(p), float(q)) for p, q, _ in data.get("bids", [])[:levels]]
        asks = [(float(p), float(q)) for p, q, _ in data.get("asks", [])[:levels]]
        return bids + asks
    except Exception:  # noqa: BLE001
        return []


def submit_order(side: str, size_usd: float, symbol: str) -> Fill:
    """Send order to Coinbase paper API or fall back to instant fill."""
    api_key = os.getenv("COINBASE_PAPER_KEY")
    endpoint = "https://api.coinbase.com/api/v3/brokerage/orders"  # paper
    if not api_key:
        price = fetch_price(symbol)
        qty = size_usd / price
        book = _order_book(symbol)
        slip_pct = random.gauss(0, 0.0001)
        fill_price = price * (1 + slip_pct if side == "buy" else 1 - slip_pct)
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
        return Fill("paper-sim", qty, fill_price)

    payload = {
        "side": side,
        "client_order_id": f"paper-{int(time.time())}",
        "product_id": symbol,
        "size": str(size_usd / fetch_price(symbol)),
        "type": "market",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    book_before = _order_book(symbol)
    start = time.perf_counter()
    for attempt in range(3):
        try:
            r = request_with_retries(
                requests.post,
                endpoint,
                json=payload,
                headers=headers,
            )
            data: dict[str, Any] = r.json()
            order_id = data.get("order_id", "paper-unknown")
            price = float(data.get("average_filled_price", fetch_price(symbol)))
            qty = float(data.get("filled_size", 0))
            latency_ms = (time.perf_counter() - start) * 1000
            book_after = _order_book(symbol)
            log_fill(
                symbol,
                side,
                qty * price,
                price,
                0.0,
                book_before=book_before,
                book_after=book_after,
                response=data,
                latency_ms=latency_ms,
            )
            return Fill(order_id, qty, price)
        except Exception:
            time.sleep(2**attempt)
    price = fetch_price(symbol)
    qty = size_usd / price
    book = _order_book(symbol)
    log_fill(symbol, side, size_usd, price, 0.0, book_before=book, book_after=book)
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
    book_before = _order_book(symbol)
    start = time.perf_counter()
    try:
        r = request_with_retries(requests.post, endpoint, json=payload, headers=headers)
        data = r.json()
        if not data.get("success", True):
            return None
        order_id = data.get("order_id", f"maker-{int(time.time())}")
        price = float(data.get("average_filled_price", fetch_price(symbol)))
        qty = float(data.get("filled_size", 0))
        if qty:
            latency_ms = (time.perf_counter() - start) * 1000
            book_after = _order_book(symbol)
            log_fill(
                symbol,
                side,
                qty * price,
                price,
                0.0,
                maker=True,
                book_before=book_before,
                book_after=book_after,
                response=data,
                latency_ms=latency_ms,
            )
            return Fill(order_id, qty, price)
    except Exception:
        pass
    return None
