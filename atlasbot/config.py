# --- traded symbols ---------------------------------------------------------
SYMBOLS = [
    "BTC-USD", "ETH-USD", "DOGE-USD", "AVAX-USD", "SUI-USD", "XLM-USD",
    "HBAR-USD", "ADA-USD", "DOT-USD", "LINK-USD", "SOL-USD",
]

# --- strategy parameters ----------------------------------------------------
SLIPPAGE_BPS = 4              # simulated slippage (basis points)
EDGE_BPS = 3                  # desired edge after costs


def profit_target(sym: str) -> float:
    """Return cost-aware profit target for *sym* as a percentage."""
    fee_bps = TAKER_FEE * 10_000
    slip = SLIPPAGE_BPS
    return (fee_bps + slip + EDGE_BPS) / 10_000
MAX_NOTIONAL_USD = 100          # risk cap per position
LOG_PATH = "data/logs/sim_tradesOverNight.csv"

# --- alpha weights ----------------------------------------------------------
W_ORDERFLOW = 0.5
W_MOMENTUM = 0.3
W_MACRO = 0.2

# --- risk limits ------------------------------------------------------------
MAX_GROSS_USD = 1_000
MAX_DAILY_LOSS = 250
RISK_PER_TRADE = 0.002

# --- execution --------------------------------------------------------------
EXECUTION_BACKEND = "sim"  # "paper" | "live" (future)

# --- data feed URLs ---------------------------------------------------------
WS_URL_PRO      = "wss://ws-feed.exchange.coinbase.com"       # legacy
WS_URL_ADVANCED = "wss://advanced-trade-ws.coinbase.com"      # new
REST_TICKER_FMT = "https://api.exchange.coinbase.com/products/{}/ticker"

# --- LLM configuration ------------------------------------------------------
import os

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- misc -----------------------------------------------------------------
LOG_HEARTBEAT_S = 60
DESK_SUMMARY_S = 600
FEE_MIN_USD = 0.10

# execution costs
TAKER_FEE = 0.0025            # Coinbase taker fee

# starting capital
START_CASH = 50_000.0

