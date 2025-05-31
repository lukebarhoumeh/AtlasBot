import argparse
import atexit
import json
import logging
import os
import signal
import time

import openai

from atlasbot import risk
from atlasbot.config import start_fee_updater
from atlasbot.metrics import start_metrics_server
from atlasbot.risk import SUMMARY_PATH
from atlasbot.secrets_loader import get_openai_api_key
from atlasbot.trader import IntradayTrader

openai.api_key = get_openai_api_key()

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

CYCLE_SEC = float(os.getenv("CYCLE_SEC", "1"))

stop_event = False
_finalised = False


def _finalize() -> None:
    global _finalised
    if _finalised:
        return
    snap = risk.portfolio_snapshot()
    snap["timestamp"] = "TOTAL"
    SUMMARY_PATH.parent.mkdir(exist_ok=True)
    with open(SUMMARY_PATH, "a") as f:
        f.write(json.dumps(snap) + "\n")
    print(f"Final equity: ${snap['equity_usd']:.2f}")
    _finalised = True


def _handle_sig(_signum, _frame) -> None:
    global stop_event
    stop_event = True
    _finalize()


signal.signal(signal.SIGINT, _handle_sig)
signal.signal(signal.SIGTERM, _handle_sig)


def _run_once(bot: IntradayTrader) -> None:
    bot.run_cycle()


def main(simulate: bool = False, max_loops: int = 0) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="sim", choices=["sim", "paper"])
    parser.add_argument("-t", "--time", type=int, default=0, help="run time seconds")
    args = parser.parse_args([] if simulate else None)

    start_fee_updater()
    start_metrics_server()
    bot = IntradayTrader(backend=args.backend)
    end_time = time.time() + args.time if args.time else None

    atexit.register(_finalize)
    loops = 0
    while not stop_event and (end_time is None or time.time() < end_time):
        if max_loops and loops >= max_loops:
            break
        _run_once(bot)
        loops += 1
        time.sleep(CYCLE_SEC)

    logger.info("Shutdown complete")
    from pathlib import Path

    import pandas as pd

    ledgers = sorted(Path("data/runs").glob("ledger_*.csv"))
    if ledgers:
        df = pd.read_csv(ledgers[-1])
        pnl = df.get("realised", df.get("realized_pnl", pd.Series([0]))).sum()
        start_cash = float(os.getenv("PAPER_CASH", "50000"))
        logger.info("Run P&L: %.2f USD  (%.2f%%)", pnl, pnl / start_cash * 100)
    _finalize()


if __name__ == "__main__":
    main()
