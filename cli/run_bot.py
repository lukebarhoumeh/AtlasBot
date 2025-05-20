import time
import openai

from atlasbot.secrets_loader import get_openai_api_key
from atlasbot.gpt_report import GPTTrendAnalyzer
from atlasbot.trader import TradingBot

openai.api_key = get_openai_api_key()

bot = TradingBot(gpt_trend_analyzer=GPTTrendAnalyzer(enabled=True))

try:
    while True:
        bot.run_cycle()
        time.sleep(5)   # outer throttle
except KeyboardInterrupt:
    print("🛑  Shutdown requested.")
