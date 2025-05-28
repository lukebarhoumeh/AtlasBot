import os
import json
import pandas as pd
from datetime import datetime, timezone
from atlasbot.config import TAKER_FEE, FEE_MIN_USD
from atlasbot import risk

PNL_PATH = "data/logs/pnl.csv"


FILL_DIR = "data/fills"


def log_fill(symbol: str, side: str, notional: float, price: float, slip: float = 0.0) -> None:
    """Print fill info and append to pnl.csv and jsonl fills."""
    fee = max(notional * TAKER_FEE, FEE_MIN_USD)
    realised, mtm = risk.record_fill(symbol, side, notional, price, fee, slip)
    ts = datetime.now(timezone.utc)
    print(
        f"[FILLED] {ts:%H:%M:%SZ}  {symbol}  {side.upper()}  ${notional:.2f} @ {price:,.2f}  fee=${fee:.2f}"
    )
    row = {
        "timestamp": ts.isoformat(),
        "symbol": symbol,
        "side": side,
        "notional": round(notional, 2),
        "price": round(price, 2),
        "fee": round(fee, 4),
        "slip": round(slip, 4),
        "realised": round(realised, 4),
        "mtm": round(mtm, 4),
    }
    os.makedirs(os.path.dirname(PNL_PATH), exist_ok=True)
    pd.DataFrame([row]).to_csv(
        PNL_PATH, mode="a", header=not os.path.exists(PNL_PATH), index=False
    )

    # persist raw fill
    os.makedirs(FILL_DIR, exist_ok=True)
    fpath = os.path.join(FILL_DIR, f"{ts.date()}.jsonl")
    with open(fpath, "a") as f:
        f.write(json.dumps(row) + "\n")


