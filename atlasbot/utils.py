import math
from statistics import mean

from atlasbot.config import SYMBOLS
from atlasbot.market_data import get_market

_md = get_market(SYMBOLS)   # singleton live feed

# --------------------------------------------------------------------------- #
def fetch_price(symbol: str) -> float:
    return _md.latest_trade(symbol)

def calculate_atr(symbol: str, period: int = 14) -> float:
    bars = _md.minute_bars(symbol)
    if len(bars) < period:
        raise RuntimeError(f"Need {period} bars for ATR.")
    tr = [h - l for (_, h, l, _) in list(bars)[-period:]]
    return mean(tr)

def fetch_volatility(symbol: str, period: int = 30) -> float:
    bars = _md.minute_bars(symbol)
    if len(bars) < period + 1:
        raise RuntimeError(f"Need {period+1} bars for σ.")
    closes = [c for *_, c in list(bars)[-(period + 1):]]
    log_r = [math.log(closes[i+1]/closes[i]) for i in range(period)]
    mu = mean(log_r)
    return math.sqrt(mean([(x - mu) ** 2 for x in log_r]))
