from prometheus_client import Gauge, Counter, start_http_server
import threading
import time

from atlasbot.market_data import get_market
from atlasbot.signals import poll_latency
from atlasbot.risk import daily_pnl, total_mtm, gross, cash, equity

ws_latency_g = Gauge('atlasbot_ws_latency_ms', 'WebSocket price latency (ms)')
rest_latency_g = Gauge('atlasbot_rest_latency_ms', 'REST poll latency (ms)')
reconnects_g = Gauge('atlasbot_reconnects_total', 'WebSocket reconnect count')
pnl_mtm_g = Gauge('atlasbot_pnl_mtm_usd', 'Mark-to-market PnL')
pnl_realised_g = Gauge('atlasbot_pnl_realised_usd', 'Realised PnL')
gross_pos_g = Gauge('atlasbot_gross_position_usd', 'Gross position USD')
cash_g = Gauge('atlasbot_cash_usd', 'Available cash')
equity_g = Gauge('atlasbot_equity_usd', 'Total account equity')
heartbeat_g = Gauge('bot_alive', 'Bot heartbeat')
gpt_errors_total = Counter('gpt_errors_total', 'GPT desk errors')
gpt_last_success_ts = Gauge('gpt_last_success_ts', 'GPT desk last success timestamp')


def start_metrics_server(port: int = 9000) -> None:
    start_http_server(port)
    threading.Thread(target=_update_loop, daemon=True).start()


def _update_loop() -> None:
    md = get_market()
    last_hb = 0.0
    while True:
        ws_latency_g.set(md.feed_latency() * 1000)
        rest_latency_g.set(poll_latency() * 1000)
        reconnects_g.set(md.reconnects)
        pnl_realised_g.set(daily_pnl())
        pnl_mtm_g.set(total_mtm())
        gross_pos_g.set(sum(gross(sym) for sym in md._symbols))
        cash_g.set(cash())
        equity_g.set(equity())
        if time.time() - last_hb >= 60:
            heartbeat_g.set(1)
            last_hb = time.time()
        time.sleep(5)

