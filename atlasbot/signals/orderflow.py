import threading
import time
import requests
from typing import Dict

from atlasbot.config import SYMBOLS

BOOK_URL = "https://api.exchange.coinbase.com/products/{}/book?level=2"

class OrderFlow:
    """Simple order book imbalance tracker using REST polling."""
    def __init__(self, symbols=SYMBOLS, poll_interval: int = 2):
        self.symbols = symbols
        self.poll_interval = poll_interval
        self._imbalance: Dict[str, float] = {s: 0.0 for s in symbols}
        self._last_poll = time.monotonic()
        threading.Thread(target=self._worker, daemon=True).start()

    # ------------------------------------------------------------------ metrics
    @property
    def last_poll_latency(self) -> float:
        return time.monotonic() - self._last_poll

    def imbalance(self, symbol: str) -> float:
        return self._imbalance.get(symbol, 0.0)

    # -------------------------------------------------------------------- worker
    def _worker(self) -> None:
        while True:
            t0 = time.monotonic()
            for sym in self.symbols:
                try:
                    r = requests.get(BOOK_URL.format(sym), timeout=2)
                    j = r.json()
                    bids = sum(float(b[1]) for b in j.get("bids", []))
                    asks = sum(float(a[1]) for a in j.get("asks", []))
                    if bids + asks:
                        self._imbalance[sym] = (bids - asks) / (bids + asks)
                except Exception:
                    pass
            self._last_poll = time.monotonic()
            time.sleep(max(0, self.poll_interval - (self._last_poll - t0)))

# single global instance
_orderflow = OrderFlow()

def imbalance(symbol: str) -> float:
    return _orderflow.imbalance(symbol)

def poll_latency() -> float:
    return _orderflow.last_poll_latency
