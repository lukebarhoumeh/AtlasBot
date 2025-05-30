import threading
import time

import requests
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

import atlasbot.risk as risk
from atlasbot.config import REST_TICKER_FMT
from atlasbot.market_data import get_market
from atlasbot.risk import cash, daily_pnl, equity, gross, maker_fill_ratio, total_mtm
from atlasbot.signals import poll_latency

REGISTRY = CollectorRegistry()
ws_latency_g = Gauge(
    "atlasbot_ws_latency_ms",
    "WebSocket price latency (ms)",
    registry=REGISTRY,
)
rest_latency_g = Gauge(
    "atlasbot_rest_latency_ms",
    "REST poll latency (ms)",
    registry=REGISTRY,
)
reconnects_g = Gauge(
    "atlasbot_reconnects_total",
    "WebSocket reconnect count",
    registry=REGISTRY,
)
pnl_mtm_g = Gauge(
    "atlasbot_pnl_mtm_usd",
    "Mark-to-market PnL",
    registry=REGISTRY,
)
pnl_realised_g = Gauge("atlasbot_pnl_realised_usd", "Realised PnL", registry=REGISTRY)
gross_pos_g = Gauge(
    "atlasbot_gross_position_usd", "Gross position USD", registry=REGISTRY
)
cash_g = Gauge("atlasbot_cash_usd", "Available cash", registry=REGISTRY)
equity_g = Gauge("atlasbot_equity_usd", "Total account equity", registry=REGISTRY)
heartbeat_g = Gauge("bot_alive", "Bot heartbeat", registry=REGISTRY)
maker_ratio_g = Gauge(
    "atlasbot_maker_fill_ratio", "Maker to total fill ratio", registry=REGISTRY
)
edge_g = Gauge("edge_bps", "Latest trade edge bps", registry=REGISTRY)
edge_hist = Histogram(
    "atlasbot_edge_bps",
    "Edge basis points distribution",
    registry=REGISTRY,
    buckets=(5, 10, 15, 20, 25, 30, 40, 50, 80, 100, 150),
)
trade_count_day_g = Gauge(
    "atlasbot_trade_count_day", "Trades executed today", registry=REGISTRY
)
macro_hit_rate_g = Gauge(
    "atlasbot_macro_hit_rate", "Macro bias hit rate", registry=REGISTRY
)
gpt_errors_total = Counter("gpt_errors_total", "GPT desk errors", registry=REGISTRY)
gpt_last_success_ts = Gauge(
    "gpt_last_success_ts", "GPT desk last success timestamp", registry=REGISTRY
)
warmup_complete_g = Gauge(
    "atlasbot_warmup_complete", "Initial bar warmup complete", registry=REGISTRY
)
feed_watchdog_total = Counter(
    "atlasbot_feed_watchdog_total",
    "Feed latency watchdog triggers",
    registry=REGISTRY,
)


def start_metrics_server(port: int = 9000) -> None:
    start_http_server(port, registry=REGISTRY)
    threading.Thread(target=_update_loop, daemon=True).start()


def _refresh_prices(symbols: list[str]) -> None:
    """Update price cache from REST endpoints for *symbols*."""
    for sym in symbols:
        try:
            r = requests.get(REST_TICKER_FMT.format(sym), timeout=5)
            if r.ok:
                get_market()._prices[sym] = float(r.json()["price"])
        except Exception:  # noqa: BLE001
            pass


def feed_watchdog_check() -> None:
    """Check feed latency and trigger watchdog if necessary."""
    md = get_market()
    if md.feed_latency() > 120:
        feed_watchdog_total.inc()
        _refresh_prices(md._symbols)


def _update_loop() -> None:
    md = get_market()
    last_hb = 0.0
    while True:
        feed_watchdog_check()
        ws_latency_g.set(md.feed_latency() * 1000)
        rest_latency_g.set(poll_latency() * 1000)
        reconnects_g.set(md.reconnects)
        pnl_realised_g.set(daily_pnl())
        pnl_mtm_g.set(total_mtm())
        gross_pos_g.set(sum(gross(sym) for sym in md._symbols))
        cash_g.set(cash())
        equity_g.set(equity())
        maker_ratio_g.set(maker_fill_ratio())
        trade_count_day_g.set(risk.trade_count_day())
        macro_hit_rate_g.set(risk.macro_hit_rate())
        warmup_complete_g.set(1 if getattr(md, "warmup_complete", False) else 0)
        if time.time() - last_hb >= 60:
            heartbeat_g.set(1)
            last_hb = time.time()
        time.sleep(5)
