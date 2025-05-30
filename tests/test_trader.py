# tests/test_trader.py
from atlasbot.gpt_report import GPTTrendAnalyzer
from atlasbot.trader import TradingBot


def test_bot_init():
    bot = TradingBot(gpt_trend_analyzer=GPTTrendAnalyzer(False))
    assert "BTC-USD" in bot.symbols
