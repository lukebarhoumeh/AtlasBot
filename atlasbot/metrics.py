from prometheus_client import Gauge, start_http_server
import threading
import time

from atlasbot.market_data import get_market
from atlasbot.signals import poll_latency
from atlasbot.risk import daily_pnl

feed_latency_g = Gauge('feed_latency_seconds', 'Price feed latency')
orderbook_latency_g = Gauge('orderbook_poll_latency_seconds', 'Orderbook poll latency')
ws_reconnects_g = Gauge('ws_reconnects_total', 'WebSocket reconnect count')
current_pnl_g = Gauge('current_pnl_usd', 'Current total PnL')


def start_metrics_server(port: int = 9000) -> None:
    start_http_server(port)
    threading.Thread(target=_update_loop, daemon=True).start()


def _update_loop() -> None:
    md = get_market()
    while True:
        feed_latency_g.set(md.feed_latency())
        orderbook_latency_g.set(poll_latency())
        ws_reconnects_g.set(md.reconnects)
        current_pnl_g.set(daily_pnl())
        time.sleep(5)
