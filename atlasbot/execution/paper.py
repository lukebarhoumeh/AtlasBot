from atlasbot.utils import fetch_price


def submit_order(side: str, size_usd: float, symbol: str) -> str:
    """Placeholder for Coinbase Advanced Trade paper API."""
    # TODO: integrate real API calls
    price = fetch_price(symbol)
    qty = size_usd / price
    return "paper-0", qty, price
