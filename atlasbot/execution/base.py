import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd

from atlasbot import risk, run_logger
from atlasbot.config import FEE_MIN_USD, TAKER_FEE

logger = logging.getLogger(__name__)

PNL_PATH = "data/logs/pnl.csv"


FILL_DIR = "data/fills"


def request_with_retries(
    method: Callable[..., Any],
    url: str,
    retries: int = 3,
    timeout: int = 5,
    **kwargs: Any,
) -> Any:
    """Return HTTP response from *method* with retry logic."""

    for attempt in range(retries):
        try:
            resp = method(url, timeout=timeout, **kwargs)
            if resp.status_code >= 500:
                time.sleep(2**attempt)
                continue
            return resp
        except Exception as exc:  # noqa: BLE001
            logger.error("HTTP request error: %s", exc)
            time.sleep(2**attempt)
    raise RuntimeError(f"Request to {url} failed after {retries} retries")


@dataclass
class Fill:
    """Order fill information."""

    order_id: str
    qty: float
    price: float


def log_fill(
    symbol: str,
    side: str,
    notional: float,
    price: float,
    slip: float = 0.0,
    maker: bool = False,
    book_before: list[tuple[float, float]] | None = None,
    book_after: list[tuple[float, float]] | None = None,
    response: dict | None = None,
    latency_ms: float | None = None,
) -> None:
    """Print fill info and append to pnl.csv and jsonl fills."""
    fee = max(notional * TAKER_FEE, FEE_MIN_USD)
    realised, mtm = risk.record_fill(symbol, side, notional, price, fee, slip, maker)
    risk.check_circuit_breaker()
    ts = datetime.now(timezone.utc)
    logger.info(
        "TRADE %s %s @ %.2f  notional=%.2f",
        side,
        symbol,
        price,
        notional,
    )
    row = {
        "timestamp": ts.isoformat(),
        "symbol": symbol,
        "side": side,
        "notional": round(notional, 2),
        "price": round(price, 2),
        "fee": round(fee, 4),
        "slip": round(slip, 4),
        "realised": round(realised, 4),
        "mtm": round(mtm, 4),
        "book_before": book_before,
        "book_after": book_after,
        "api_response": response,
        "latency_ms": round(latency_ms or 0.0, 2),
    }
    os.makedirs(os.path.dirname(PNL_PATH), exist_ok=True)
    pd.DataFrame([row]).to_csv(
        PNL_PATH, mode="a", header=not os.path.exists(PNL_PATH), index=False
    )
    run_logger.append(row)

    # persist raw fill
    os.makedirs(FILL_DIR, exist_ok=True)
    fpath = os.path.join(FILL_DIR, f"{ts.date()}.jsonl")
    with open(fpath, "a") as f:
        f.write(json.dumps(row) + "\n")


def submit_maker_order(side: str, size_usd: float, symbol: str) -> Fill | None:
    """Submit a maker (post-only) order. Return fill details or None."""
    raise NotImplementedError


def maker_to_taker(
    exec_api: object, side: str, size_usd: float, symbol: str, wait_s: int = 5
) -> Fill:
    """Attempt maker then fall back to IOC market order.

    Args:
        exec_api: Execution module with submit_maker_order and submit_order.
        side: Order side ("buy" or "sell").
        size_usd: Order notional in USD.
        symbol: Trading symbol.
        wait_s: Seconds to wait for maker fill before falling back.

    Returns:
        Fill: Order fill details from the executed order.
    """
    if hasattr(exec_api, "submit_maker_order"):
        filled = exec_api.submit_maker_order(side, size_usd, symbol)
        if filled:
            return filled
    time.sleep(wait_s)
    return exec_api.submit_order(side, size_usd, symbol)
