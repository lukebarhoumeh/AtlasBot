"""
Real-time Coinbase price streamer + minute-bar cache.
Keeps a thread-safe dict of the latest trade price per symbol and
builds rolling OHLCV bars for ATR / volatility calculations.
"""
import json, logging, threading, time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Dict, Deque, List, Tuple

import cbpro  # pip install cbpro

ONE_MIN = 60  # seconds


class _CBWebSocket(cbpro.WebsocketClient):
    """
    Lightweight wrapper around cbpro.WebsocketClient that only
    listens to the 'ticker' channel and stashes the last trade price.
    """

    def __init__(self, products: List[str], price_store: Dict[str, float]):
        super().__init__(
            url="wss://ws-feed.exchange.coinbase.com",
            products=products,
            channels=["ticker"],
        )
        self._price_store = price_store

    def on_message(self, msg):
        if msg.get("type") != "ticker":
            return
        try:
            product = msg["product_id"]
            price = float(msg["price"])
            self._price_store[product] = price
        except (KeyError, ValueError):
            logging.warning(f"Malformed ticker message: {msg}")

    # We keep on_error/on_close defaults; cbpro auto-reconnects.


class MarketData:
    """
    Singleton providing:
      • latest_trade(symbol)  -> float
      • minute_bars(symbol)   -> deque[Tuple[open, high, low, close]]
    """

    _instance = None

    def __new__(cls, symbols: List[str]):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(symbols)
        return cls._instance

    # ---------- public API ----------
    def latest_trade(self, symbol: str) -> float:
        price = self._prices.get(symbol)
        if price is None:
            raise RuntimeError(f"No live price yet for {symbol}")
        return price

    def minute_bars(self, symbol: str) -> Deque[Tuple[float, float, float, float]]:
        return self._bars[symbol]

    # ---------- internal ----------
    def _init(self, symbols: List[str]):
        self._prices: Dict[str, float] = {}
        self._bars: Dict[
            str, Deque[Tuple[float, float, float, float]]
        ] = {s: deque(maxlen=5000) for s in symbols}  # ≈ 3½ days @ 1-min
        self._symbols = symbols

        # Start WebSocket thread
        self._ws = _CBWebSocket(symbols, self._prices)
        self._ws_thread = threading.Thread(
            target=self._ws.start, name="CBWebSocket", daemon=True
        )
        self._ws_thread.start()

        # Start minute-bar worker
        self._bar_thread = threading.Thread(
            target=self._bar_worker, name="BarBuilder", daemon=True
        )
        self._bar_thread.start()

    def _bar_worker(self):
        """
        Every minute build OHLCV bars off the stored last-trade prices.
        We only need OHLC for ATR, but we reserve V (volume) placeholder
        for future order-book integration.
        """
        last_minute = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        ohlc: Dict[str, List[float]] = defaultdict(list)

        while True:
            now = datetime.now(timezone.utc)
            symbol_prices_snapshot = self._prices.copy()

            # Accumulate intra-minute ticks
            for sym, price in symbol_prices_snapshot.items():
                ohlc[sym].append(price)

            # Roll bar on minute switch
            if now - last_minute >= timedelta(seconds=ONE_MIN):
                for sym, prices in ohlc.items():
                    if prices:
                        o, h, l, c = prices[0], max(prices), min(prices), prices[-1]
                        self._bars[sym].append((o, h, l, c))
                ohlc = defaultdict(list)
                last_minute = now
            time.sleep(1)


# helper to expose singleton easily
_market = None


def get_market(symbols: List[str]):
    global _market
    if _market is None:
        _market = MarketData(symbols)
    return _market
