from prometheus_client import Gauge, start_http_server
import threading
import time

from atlasbot.market_data import get_market
from atlasbot.signals import poll_latency
from atlasbot.risk import daily_pnl, total_mtm, gross

ws_latency_g = Gauge('atlasbot_ws_latency_ms', 'WebSocket price latency (ms)')
rest_latency_g = Gauge('atlasbot_rest_latency_ms', 'REST poll latency (ms)')
reconnects_g = Gauge('atlasbot_reconnects_total', 'WebSocket reconnect count')
pnl_mtm_g = Gauge('atlasbot_pnl_mtm_usd', 'Mark-to-market PnL')
pnl_realised_g = Gauge('atlasbot_pnl_realised_usd', 'Realised PnL')
gross_pos_g = Gauge('atlasbot_gross_position_usd', 'Gross position USD')


def start_metrics_server(port: int = 9000) -> None:
    start_http_server(port)
    threading.Thread(target=_update_loop, daemon=True).start()


def _update_loop() -> None:
    md = get_market()
    while True:
        ws_latency_g.set(md.feed_latency() * 1000)
        rest_latency_g.set(poll_latency() * 1000)
        reconnects_g.set(md.reconnects)
        pnl_realised_g.set(daily_pnl())
        pnl_mtm_g.set(total_mtm())
        gross_pos_g.set(sum(gross(sym) for sym in md._symbols))
        time.sleep(5)

