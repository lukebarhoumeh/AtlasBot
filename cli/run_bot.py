import argparse
import time
import openai

from atlasbot.secrets_loader import get_openai_api_key
from atlasbot.trader import IntradayTrader
from atlasbot.metrics import start_metrics_server

openai.api_key = get_openai_api_key()

parser = argparse.ArgumentParser()
parser.add_argument("--backend", default="sim", choices=["sim", "paper"])
args = parser.parse_args()

start_metrics_server()
bot = IntradayTrader(backend=args.backend)

try:
    while True:
        bot.run_cycle()
        time.sleep(5)   # outer throttle
except KeyboardInterrupt:
    print("🛑  Shutdown requested.")
