# tests/test_trader.py
from atlasbot.trader import TradingBot
from atlasbot.gpt_report import GPTTrendAnalyzer

def test_bot_init():
    bot = TradingBot(gpt_trend_analyzer=GPTTrendAnalyzer(False))
    assert "BTC-USD" in bot.symbols
