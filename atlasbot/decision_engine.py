from math import copysign
from atlasbot.signals import imbalance, momentum, macro_bias
from atlasbot.config import W_ORDERFLOW, W_MOMENTUM, W_MACRO

class DecisionEngine:
    """Combine multiple signals into a trading bias."""

    def next_advice(self, symbol: str) -> dict:
        im = imbalance(symbol)
        mo = momentum(symbol)
        ma = macro_bias(symbol)
        score = W_ORDERFLOW * im + W_MOMENTUM * mo + W_MACRO * ma
        bias = "long" if score > 0 else "short" if score < 0 else "flat"
        return {
            "bias": bias,
            "confidence": abs(score),
            "rationale": {
                "orderflow": im,
                "momentum": mo,
                "macro": ma,
            },
        }
