from atlasbot import trader, secrets_loader
from trader import CoinbaseTrader

bot = CoinbaseTrader()

print("\n📈 BTC-USD Best Bid/Ask:")
print(bot.get_best_bid_ask("BTC-USD"))
