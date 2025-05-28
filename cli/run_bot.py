import argparse
import time
import signal
import os
import logging
import openai

from atlasbot.secrets_loader import get_openai_api_key
from atlasbot.trader import IntradayTrader
from atlasbot.metrics import start_metrics_server

openai.api_key = get_openai_api_key()

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level)

parser = argparse.ArgumentParser()
parser.add_argument("--backend", default="sim", choices=["sim", "paper"])
parser.add_argument("-t", "--time", type=int, default=0, help="run time seconds")
args = parser.parse_args()

start_metrics_server()
bot = IntradayTrader(backend=args.backend)
stop_event = False
end_time = time.time() + args.time if args.time else None


def _handle_sig(_signum, _frame):
    global stop_event
    stop_event = True


signal.signal(signal.SIGINT, _handle_sig)
signal.signal(signal.SIGTERM, _handle_sig)

while not stop_event and (end_time is None or time.time() < end_time):
    bot.run_cycle()
    time.sleep(5)

print("🛑  Shutdown requested.")
from atlasbot import risk
risk.snapshot()
