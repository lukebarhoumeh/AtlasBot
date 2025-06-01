"""Utility for summarizing trading logs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from .execution import base


def summarize(log_path: str = base.PNL_PATH) -> Dict[str, float]:
    """Return summary statistics for a trading session.

    Args:
        log_path: Path to trade log CSV.

    Returns:
        Dictionary with trade count, win rate, max drawdown and average latency.
    """

    path = Path(log_path)
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if len(df) == 0:
        return {}
    realised = df.get("realised", [])
    mtm = df.get("mtm", [])
    pnl = [r + m for r, m in zip(realised, mtm)]
    trades = len(pnl)
    wins = sum(1 for p in pnl if p > 0)
    win_rate = wins / trades if trades else 0.0
    cum = 0.0
    high = 0.0
    drawdown = 0.0
    for r in pnl:
        cum += r
        high = max(high, cum)
        drawdown = min(drawdown, cum - high)
    latency = df.get("latency_ms") or []
    avg_latency = sum(latency) / len(latency) if latency else 0.0
    return {
        "trades": trades,
        "win_rate": win_rate,
        "max_drawdown": drawdown,
        "avg_latency_ms": avg_latency,
    }
