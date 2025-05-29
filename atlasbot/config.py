# --- traded symbols ---------------------------------------------------------
import os

SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "DOGE-USD",
    "AVAX-USD",
    "SUI-USD",
    "XLM-USD",
    "HBAR-USD",
    "ADA-USD",
    "DOT-USD",
    "LINK-USD",
    "SOL-USD",
]

# --- strategy parameters ----------------------------------------------------
SLIPPAGE_BPS = 4  # simulated slippage (basis points)
# fee and minimum edge thresholds
FEE_BPS = int(0.0025 * 10_000)
FEE_FLAT = 0.10
MIN_EDGE_BPS = 3
CURRENT_TAKER_BPS = FEE_BPS
CURRENT_MAKER_BPS = FEE_BPS


def profit_target(sym: str) -> float:
    """Return cost-aware profit target for *sym* as a percentage."""
    fee_bps = FEE_BPS
    slip = SLIPPAGE_BPS
    return (fee_bps + slip + MIN_EDGE_BPS) / 10_000


MAX_NOTIONAL_USD = 100  # risk cap per position
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
WS_URL_PRO = "wss://ws-feed.exchange.coinbase.com"  # legacy
WS_URL_ADVANCED = "wss://advanced-trade-ws.coinbase.com"  # new
REST_TICKER_FMT = "https://api.exchange.coinbase.com/products/{}/ticker"

# --- LLM configuration ------------------------------------------------------
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- misc -----------------------------------------------------------------
LOG_HEARTBEAT_S = 60
DESK_SUMMARY_S = 600
FEE_MIN_USD = FEE_FLAT

# execution costs
TAKER_FEE = 0.0025  # Coinbase taker fee

# starting capital
START_CASH = 50_000.0


_last_fee_check = 0.0


def refresh_fee_tier() -> None:
    """Refresh maker/taker fees from Coinbase and adjust edge threshold."""
    global CURRENT_MAKER_BPS, CURRENT_TAKER_BPS, MIN_EDGE_BPS, _last_fee_check
    import time

    import requests

    if time.time() - _last_fee_check < 3600:
        return
    try:
        r = requests.get("https://api.exchange.coinbase.com/fees", timeout=5)
        if r.ok:
            j = r.json()
            CURRENT_MAKER_BPS = int(float(j.get("maker_fee_rate", 0)) * 10_000)
            CURRENT_TAKER_BPS = int(float(j.get("taker_fee_rate", 0)) * 10_000)
            MIN_EDGE_BPS = 2 if CURRENT_TAKER_BPS < FEE_BPS else 3
            _last_fee_check = time.time()
    except Exception:  # noqa: BLE001
        pass


def start_fee_updater() -> None:
    """Start background thread for hourly fee updates."""
    import threading
    import time

    def _loop() -> None:
        while True:
            refresh_fee_tier()
            time.sleep(3600)

    threading.Thread(target=_loop, daemon=True).start()
