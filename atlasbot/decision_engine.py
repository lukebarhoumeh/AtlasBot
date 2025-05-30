import json
import os
import time
from pathlib import Path

import numpy as np

from atlasbot import risk
from atlasbot.config import (
    BREAKOUT_WEIGHT,
    W_MACRO,
    W_MOMENTUM,
    W_ORDERFLOW,
    profit_target,
)
from atlasbot.signals import breakout, imbalance, macro_bias, momentum

ADAPT_TEMP = float(os.getenv("ADAPT_TEMP", "2.0"))
WEIGHTS_FILE = Path("data/weights.json")


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
        bias = "long" if score > 0 else "short" if score < 0 else "flat"
        # scale edge so strong signals clear execution costs
        raw_edge = profit_target(symbol) * score * 2
        return {
            "bias": bias,
            "confidence": abs(score),
            "edge": raw_edge,
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
                corr = float(np.corrcoef(sigs, returns)[0, 1])
                if np.isnan(corr):
                    corr = 0.0
            edges[key] = corr
        vals = np.array([edges[k] * ADAPT_TEMP for k in edges])
        exps = np.exp(vals - np.max(vals))
        w = exps / exps.sum()
        self.weights = dict(zip(edges.keys(), w))
        WEIGHTS_FILE.parent.mkdir(exist_ok=True)
        with open(WEIGHTS_FILE, "w") as f:
            json.dump({"ts": time.time(), **self.weights}, f)
        self._last_adapt = time.time()
