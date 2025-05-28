# --- traded symbols ---------------------------------------------------------
SYMBOLS = [
    "BTC-USD", "ETH-USD", "DOGE-USD", "AVAX-USD", "SUI-USD", "XLM-USD",
    "HBAR-USD", "ADA-USD", "DOT-USD", "LINK-USD", "SOL-USD",
]

# --- strategy parameters ----------------------------------------------------
PROFIT_TARGETS = {
    "BTC-USD": 0.0015, "ETH-USD": 0.0020, "DOGE-USD": 0.0060,
    "AVAX-USD": 0.0050, "SUI-USD": 0.0050, "XLM-USD": 0.0040,
    "HBAR-USD": 0.0035, "ADA-USD": 0.0025, "DOT-USD": 0.0040,
    "LINK-USD": 0.0030, "SOL-USD": 0.0030,
}
MAX_NOTIONAL_USD = 100          # risk cap per position
LOG_PATH = "data/logs/sim_tradesOverNight.csv"

# --- alpha weights ----------------------------------------------------------
W_ORDERFLOW = 0.5
W_MOMENTUM = 0.3
W_MACRO = 0.2

# --- risk limits ------------------------------------------------------------
MAX_GROSS_USD = 1_000
MAX_DAILY_LOSS = 100

# --- execution --------------------------------------------------------------
EXECUTION_BACKEND = "sim"  # "paper" | "live" (future)

# --- data feed URLs ---------------------------------------------------------
WS_URL_PRO      = "wss://ws-feed.exchange.coinbase.com"       # legacy
WS_URL_ADVANCED = "wss://advanced-trade-ws.coinbase.com"      # new
REST_TICKER_FMT = "https://api.exchange.coinbase.com/products/{}/ticker"

# --- LLM configuration ------------------------------------------------------
import os

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
