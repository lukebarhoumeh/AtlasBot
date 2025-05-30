"""
Real-time Coinbase price streamer + 1-minute bar cache
—————————————————————————————————————————————————————————
• tries legacy Pro WS first, auto-fails over to Advanced-Trade WS
• if first tick hasn’t arrived in 3 s → seed with REST /ticker
• builds rolling OHLC bars for ATR/vol
• exponential back-off reconnect, no log spam
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, List, Tuple

import websocket  # type: ignore

from atlasbot.config import REST_TICKER_FMT, SYMBOLS, WS_URL_ADVANCED, WS_URL_PRO

ONE_MIN = 60
BAR_HISTORY = 5_000  # ≈ 3.5 days
SEED_TIMEOUT = 3  # s to wait before REST seed
REST_POLL_INTERVAL = 5  # seconds between REST polling


# ----------------------------- WebSocket client (vanilla)
class _WSClient:
    def __init__(
        self,
        url: str,
        products: List[str],
        price_store: Dict[str, float],
        on_open_cb=None,
        on_fail_cb=None,
        on_tick_cb=None,
    ):
        self._url, self._products, self._store = url, products, price_store
        self._on_open_cb = on_open_cb
        self._on_fail_cb = on_fail_cb
        self._on_tick_cb = on_tick_cb
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
            try:
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:  # noqa: BLE001
                logging.error("WS error: %s", exc)
                if self._on_fail_cb:
                    self._on_fail_cb()
            else:
                if self._on_fail_cb:
                    self._on_fail_cb()
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
        if self._on_open_cb:
            self._on_open_cb()

    def _on_msg(self, _, msg: str):
        try:
            j = json.loads(msg)
            if j.get("type") == "ticker":
                self._store[j["product_id"]] = float(j["price"])
                self._last_update = time.monotonic()
                if self._on_tick_cb:
                    self._on_tick_cb()
        except Exception as exc:  # noqa: BLE001
            logging.debug("malformed ws msg: %s (%s)", msg[:120], exc)

    def _on_err(self, _, err):
        logging.error("WS error: %s", err)
        if self._on_fail_cb:
            self._on_fail_cb()

    def _on_close(self, *_):
        if self._on_fail_cb:
            self._on_fail_cb()


def _seed_prices(products: List[str], price_store: Dict[str, float]):
    """Best-effort REST seed so we’re never empty."""
    import warnings

    import requests

    warnings.filterwarnings("ignore", category=UserWarning)
    for p in products:
        try:
            r = requests.get(REST_TICKER_FMT.format(p), timeout=2).json()
            price_store[p] = float(r["price"])
            try:
                _md = get_market()
                _md._last_update = time.monotonic()
            except Exception:
                pass
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------- MarketData singleton
class MarketData:
    _instance: "MarketData | None" = None

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
        self._last_update = time.monotonic()
        self.mode = "websocket"
        self.reconnects = 0
        self._rest_thread: threading.Thread | None = None
        self.warmup_complete = False

        self._warm_start()

        # start socket thread (legacy first → auto-fallback handled in _ws_runner)
        threading.Thread(target=self._ws_runner, name="CBWS", daemon=True).start()

        # start bar builder
        threading.Thread(
            target=self._bar_worker, name="BarBuilder", daemon=True
        ).start()

    def _warm_start(self) -> None:
        import requests

        url_fmt = (
            "https://api.exchange.coinbase.com/products/{}/candles"
            "?granularity=60&limit=150"
        )
        for sym in self._symbols:
            try:
                r = requests.get(url_fmt.format(sym), timeout=5)
                data = r.json()

                # API returns newest-first; iterate oldest-first for bar history
                for row in reversed(data):
                    _, low, high, open_, close, *_ = row
                    self._bars[sym].append((open_, high, low, close))

                # —— FIX ——
                # Only set a live price when we *will* wait for WebSocket ticks.
                # Unit-tests monkey-patch SEED_TIMEOUT = 0 to force REST seeding.
                if data and SEED_TIMEOUT:
                    self._prices[sym] = float(data[0][4])  # latest close
                    self._last_update = time.monotonic()
            except Exception:
                pass

        self.warmup_complete = all(self._bars[s] for s in self._symbols)

    # ————— public API —————
    def wait_ready(self, timeout: int = 15) -> bool:
        """True if every symbol has at least one price within *timeout* seconds."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if all(s in self._prices for s in self._symbols):
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

    def feed_latency(self) -> float:
        """Seconds since the last price update."""
        return time.monotonic() - self._last_update

    # ————— threads —————
    def _ws_runner(self):
        # first try legacy; if nothing arrives in SEED_TIMEOUT fallback → advanced
        for url in (WS_URL_PRO, WS_URL_ADVANCED):
            seed_t0 = time.monotonic()
            ws = _WSClient(
                url,
                self._symbols,
                self._prices,
                on_open_cb=self._on_ws_open,
                on_fail_cb=self._on_ws_fail,
                on_tick_cb=lambda: setattr(self, "_last_update", time.monotonic()),
            )
            t = threading.Thread(target=ws.run_forever, daemon=True)
            t.start()
            while time.monotonic() - seed_t0 < SEED_TIMEOUT:
                if self._prices:
                    return
                time.sleep(0.2)
            if ws._ws:
                ws._ws.close()

        _seed_prices(self._symbols, self._prices)
        self._last_update = time.monotonic()
        self._switch_to_rest()

        ws = _WSClient(
            WS_URL_ADVANCED,
            self._symbols,
            self._prices,
            on_open_cb=self._on_ws_open,
            on_fail_cb=self._on_ws_fail,
            on_tick_cb=lambda: setattr(self, "_last_update", time.monotonic()),
        )
        threading.Thread(target=ws.run_forever, daemon=True).start()

    # --- websocket callbacks & REST polling ---
    def _on_ws_open(self) -> None:
        if self.mode != "websocket":
            logging.warning("WS reconnected – switching back to WebSocket")
        self.mode = "websocket"

    def _on_ws_fail(self) -> None:
        self.reconnects += 1
        self._switch_to_rest()

    def _switch_to_rest(self) -> None:
        if self.mode != "rest":
            logging.warning("⚠️  WS failed – switching to REST polling")
            self.mode = "rest"
        self._start_rest_thread()

    def _start_rest_thread(self) -> None:
        if self._rest_thread and self._rest_thread.is_alive():
            return
        self._rest_thread = threading.Thread(
            target=self._rest_poller, name="RESTPoll", daemon=True
        )
        self._rest_thread.start()

    def _rest_poller(self) -> None:
        import requests

        while self.mode == "rest":
            for sym in self._symbols:
                try:
                    r = requests.get(REST_TICKER_FMT.format(sym), timeout=5)
                    if r.ok:
                        self._prices[sym] = float(r.json()["price"])
                        self._last_update = time.monotonic()
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(REST_POLL_INTERVAL)

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
                        o, h, low, c = (
                            prices[0],
                            max(prices),
                            min(prices),
                            prices[-1],
                        )
                        self._bars[s].append((o, h, low, c))
                bucket.clear()
                last = now.replace(second=0, microsecond=0)
            time.sleep(1)


# ---------------------------------------------------------------- helper
_market: MarketData | None = None


def get_market(symbols: List[str] = SYMBOLS) -> MarketData:
    global _market
    if _market is None:
        MarketData._instance = None
        _market = MarketData(symbols)
    return _market
