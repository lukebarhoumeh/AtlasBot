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

parser = argparse.ArgumentParser()
parser.add_argument("--backend", default="sim", choices=["sim", "paper"])
parser.add_argument("-t", "--time", type=int, default=0, help="run time seconds")
args = parser.parse_args()

start_fee_updater()
start_metrics_server()
bot = IntradayTrader(backend=args.backend)
stop_event = False
end_time = time.time() + args.time if args.time else None

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


atexit.register(_finalize)


def _handle_sig(_signum, _frame):
    global stop_event
    stop_event = True
    _finalize()


signal.signal(signal.SIGINT, _handle_sig)
signal.signal(signal.SIGTERM, _handle_sig)

while not stop_event and (end_time is None or time.time() < end_time):
    bot.run_cycle()
    time.sleep(5)

print("🛑  Shutdown requested.")
_finalize()
