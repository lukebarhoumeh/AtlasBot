import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from math import exp
from pathlib import Path

from numpy import corrcoef as _corr

from atlasbot import risk
from atlasbot.config import (BREAKOUT_WEIGHT, FEE_BPS, MIN_EDGE_BPS,
                             SLIPPAGE_BPS, W_MACRO, W_MOMENTUM, W_ORDERFLOW)
from atlasbot.market_data import get_spread_bps
from atlasbot.run_logger import log_decision
from atlasbot.signals import breakout, imbalance, macro_bias, momentum
from atlasbot.utils import fetch_price

ADAPT_TEMP = float(os.getenv("ADAPT_TEMP", "2.0"))
WEIGHTS_FILE = Path("data/weights.json")

# price history for hybrid signal
_tick_history: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=10))
_window_history: dict[str, deque[tuple[float, float]]] = defaultdict(lambda: deque())


def _zscore(seq: list[float]) -> float:
    if len(seq) < 2:
        return 0.0
    mean = sum(seq) / len(seq)
    var = sum((x - mean) ** 2 for x in seq) / len(seq)
    std = var**0.5
    return 0.0 if std == 0 else (seq[-1] - mean) / std


def hybrid_signal(symbol: str) -> float:
    """Return 30 s momentum z-score plus 10-tick mean reversion."""
    price = fetch_price(symbol)
    _tick_history[symbol].append(price)
    now = time.time()
    window = _window_history[symbol]
    window.append((now, price))
    while window and now - window[0][0] > 30:
        window.popleft()
    momentum = _zscore([p for _, p in window])
    ticks = _tick_history[symbol]
    mean_rev = 0.0
    if ticks:
        avg = sum(ticks) / len(ticks)
        if avg:
            mean_rev = -(price - avg) / avg
    score = momentum + mean_rev
    return max(-1.0, min(1.0, score))


def expected_edge_bps(
    signal: float,
    tick_size: float,
    mid_px: float,
    fee_bps: int,
    slippage_bps: int,
) -> float:
    """Return expected edge in basis points."""
    return 1e4 * (signal * tick_size / mid_px) - fee_bps - slippage_bps


class DecisionEngine:
    """Combine multiple signals into a trading bias with adaptive weights."""

    def __init__(self) -> None:
        self.weights = {
            "orderflow": W_ORDERFLOW,
            "momentum": W_MOMENTUM,
            "macro": W_MACRO,
            "breakout": BREAKOUT_WEIGHT,
        }
        self._last_adapt = 0.0

    # --------------------------------------------------------------- public API
    def next_advice(self, symbol: str) -> dict:
        """Return trading advice for *symbol* with scaled edge."""
        start = time.perf_counter_ns()
        if time.time() - self._last_adapt >= 3600:
            self._adapt_weights()
        im = imbalance(symbol)
        mo = momentum(symbol)
        ma = macro_bias(symbol)
        br = breakout(symbol)
        score = (
            self.weights["orderflow"] * im
            + self.weights["momentum"] * mo
            + self.weights["macro"] * ma
            + self.weights["breakout"] * br
        )
        price = fetch_price(symbol)
        bias = "long" if score > 0 else "short" if score < 0 else "flat"
        edge_bps = expected_edge_bps(score, 0.01, price, FEE_BPS, SLIPPAGE_BPS)
        latency_ms = (time.perf_counter_ns() - start) / 1e6
        log_decision(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "px": price,
                "side": bias,
                "edge_bps": edge_bps,
                "score": score,
                "latency_ms": latency_ms,
                "spread_bps": get_spread_bps(symbol),
                "order_id": "",
            }
        )
        if edge_bps < MIN_EDGE_BPS:
            bias = "flat"
        return {
            "bias": bias,
            "confidence": abs(score),
            "edge": edge_bps / 10_000,
            "rationale": {
                "orderflow": im,
                "momentum": mo,
                "macro": ma,
                "breakout": br,
            },
        }

    # --------------------------------------------------------------- internals
    def _adapt_weights(self, n: int = 200) -> None:
        trades = risk.last_fills(n)
        if not trades:
            return
        returns = [t.get("return", 0.0) for t in trades]
        if len(set(returns)) <= 1:
            return
        edges = {}
        for key in ("orderflow", "momentum", "macro", "breakout"):
            sigs = [t.get("signals", {}).get(key, 0.0) for t in trades]
            if len(set(sigs)) <= 1:
                corr = 0.0
            else:
                try:
                    corr = float(_corr(sigs, returns)[0, 1])
                except Exception:
                    corr = 0.0
            edges[key] = corr
        vals = [edges[k] * ADAPT_TEMP for k in edges]
        m = max(vals)
        exps = [exp(v - m) for v in vals]
        total = sum(exps)
        weights = [e / total for e in exps]
        self.weights = dict(zip(edges.keys(), weights))
        WEIGHTS_FILE.parent.mkdir(exist_ok=True)
        with open(WEIGHTS_FILE, "w") as f:
            json.dump({"ts": time.time(), **self.weights}, f)
        self._last_adapt = time.time()
