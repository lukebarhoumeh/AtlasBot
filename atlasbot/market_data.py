"""
Real-time Coinbase price streamer + 1-minute bar cache
—————————————————————————————————————————————————————————
• tries legacy Pro WS first, auto-fails over to Advanced-Trade WS
• if first tick hasn’t arrived in 3 s -> seed with REST /ticker
• builds rolling OHLC bars for ATR/vol
• exponential back-off reconnect, no log spam
"""

from __future__ import annotations
import json, logging, threading, time, websocket
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, List, Tuple

from atlasbot.config import (SYMBOLS, WS_URL_PRO,
                             WS_URL_ADVANCED, REST_TICKER_FMT)

ONE_MIN       = 60
BAR_HISTORY   = 5_000             # ≈ 3.5 days
SEED_TIMEOUT  = 3                 # s to wait before REST seed


# ---------------------------------------------------------------- WebSocket client (vanilla)
class _WSClient:
    def __init__(self, url: str, products: List[str], price_store: Dict[str, float]):
        self._url, self._products, self._store = url, products, price_store
        self._ws: websocket.WebSocketApp | None = None

    # ————— public —————
    def run_forever(self):
        backoff = 1
        while True:
            self._ws = websocket.WebSocketApp(
                self._url,
                on_open=self._on_open,
                on_message=self._on_msg,
                on_error=self._on_err,
                on_close=self._on_close,
            )
            self._ws.run_forever(ping_interval=20, ping_timeout=10)
            logging.error("WS closed – retrying in %ds", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

    # ————— internals —————
    def _on_open(self, _):
        print("-- Subscribed! --")
        sub = {
            "type": "subscribe",
            "product_ids": self._products,
            "channels": ["ticker"],
        }
        self._ws.send(json.dumps(sub))

    def _on_msg(self, _, msg: str):
        try:
            j = json.loads(msg)
            if j.get("type") == "ticker":
                self._store[j["product_id"]] = float(j["price"])
        except Exception as exc:                         # noqa: BLE001
            logging.debug("malformed ws msg: %s (%s)", msg[:120], exc)

    def _on_err(self, _, err):
        logging.error("WS error: %s", err)

    def _on_close(self, *_):
        pass


def _seed_prices(products: List[str], price_store: Dict[str, float]):
    """Best-effort REST seed so we’re never empty."""
    import requests, warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    for p in products:
        try:
            r = requests.get(REST_TICKER_FMT.format(p), timeout=2).json()
            price_store[p] = float(r["price"])
        except Exception:                                # noqa: BLE001
            pass


# ---------------------------------------------------------------- MarketData singleton
class MarketData:
    _instance: "MarketData|None" = None

    def __new__(cls, symbols: List[str]):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(symbols)
        return cls._instance

    # ————— internal init —————
    def _init(self, symbols: List[str]):
        self._symbols = symbols
        self._prices: Dict[str, float] = {}
        self._bars: Dict[str, Deque[Tuple[float, float, float, float]]] = {
            s: deque(maxlen=BAR_HISTORY) for s in symbols
        }

        # start socket thread (legacy first → auto-fallback handled in _ws_runner)
        threading.Thread(
            target=self._ws_runner, name="CBWS", daemon=True
        ).start()

        # start bar builder
        threading.Thread(
            target=self._bar_worker, name="BarBuilder", daemon=True
        ).start()

    # ————— public API —————
    def wait_ready(self, timeout: int = 15) -> bool:
        """True if at least one price arrives within *timeout* seconds."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._prices:
                return True
            time.sleep(0.2)
        return False

    def latest_trade(self, sym: str) -> float:
        try:
            return self._prices[sym]
        except KeyError as exc:
            raise RuntimeError(f"No live price yet for {sym}") from exc

    def minute_bars(self, sym: str) -> Deque[Tuple[float, float, float, float]]:
        return self._bars[sym]

    # ————— threads —————
    def _ws_runner(self):
        # first try legacy; if nothing arrives in SEED_TIMEOUT fallback ➜ advanced
        for url in (WS_URL_PRO, WS_URL_ADVANCED):
            seed_t0 = time.monotonic()
            ws = _WSClient(url, self._symbols, self._prices)
            t = threading.Thread(target=ws.run_forever, daemon=True)
            t.start()
            # wait a bit – if prices arrive we’re done
            while time.monotonic() - seed_t0 < SEED_TIMEOUT:
                if self._prices:
                    break
                time.sleep(0.2)
            if self._prices:
                return  # success on this URL
            # else: stop thread & try next
            if ws._ws:
                ws._ws.close()
        # nothing yet -> REST seed so the bot can start sizing
        _seed_prices(self._symbols, self._prices)

    def _bar_worker(self):
        last = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        bucket: Dict[str, List[float]] = defaultdict(list)
        while True:
            now = datetime.now(timezone.utc)
            for s, px in self._prices.items():
                bucket[s].append(px)
            if now >= last + timedelta(minutes=1):
                for s, prices in bucket.items():
                    if prices:
                        o, h, l, c = prices[0], max(prices), min(prices), prices[-1]
                        self._bars[s].append((o, h, l, c))
                bucket.clear()
                last = now.replace(second=0, microsecond=0)
            time.sleep(1)


# ---------------------------------------------------------------- helper
_market: MarketData | None = None


def get_market(symbols: List[str] = SYMBOLS) -> MarketData:
    global _market
    if _market is None:
        _market = MarketData(symbols)
    return _market
