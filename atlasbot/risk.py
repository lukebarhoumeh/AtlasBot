from __future__ import annotations

import os
from datetime import datetime, timezone
import pandas as pd

from atlasbot.config import (
    MAX_GROSS_USD,
    MAX_DAILY_LOSS,
)
from atlasbot.utils import fetch_price

PNL_PATH = "data/logs/pnl.csv"
DAILY_PATH = "data/logs/daily_pnl.csv"


class RiskManager:
    def __init__(self):
        self.lots: dict[str, list[tuple[float, float]]] = {}
        self.realised = {}
        self.daily_pnl = 0.0
        self._last_snapshot = datetime.now(timezone.utc).date()
        self.trades: list[dict] = []

    def _update_inventory(self, symbol: str, qty: float, price: float) -> float:
        lots = self.lots.setdefault(symbol, [])
        realised = 0.0
        if qty > 0:
            while qty and lots and lots[0][0] < 0:
                lqty, lprice = lots[0]
                close = min(qty, -lqty)
                realised += (lprice - price) * close
                lqty += close
                qty -= close
                if lqty == 0:
                    lots.pop(0)
                else:
                    lots[0] = (lqty, lprice)
            if qty:
                lots.append((qty, price))
        else:
            qty = -qty
            while qty and lots and lots[0][0] > 0:
                lqty, lprice = lots[0]
                close = min(qty, lqty)
                realised += (price - lprice) * close
                lqty -= close
                qty -= close
                if lqty == 0:
                    lots.pop(0)
                else:
                    lots[0] = (lqty, lprice)
            if qty:
                lots.append((-qty, price))
        self.realised[symbol] = self.realised.get(symbol, 0.0) + realised
        return realised

    def gross(self, symbol: str) -> float:
        return sum(abs(q) * p for q, p in self.lots.get(symbol, []))

    def check_risk(self, symbol: str, side: str, size_usd: float) -> bool:
        pos = self.gross(symbol)
        new_pos = pos + size_usd if side == "buy" else pos - size_usd
        if abs(new_pos) > MAX_GROSS_USD:
            return False
        if self.daily_pnl <= -MAX_DAILY_LOSS:
            return False
        return True

    def record_fill(
        self, symbol: str, side: str, notional: float, price: float, fee: float, slip: float
    ) -> tuple[float, float]:
        qty = notional / price
        qty = qty if side == "buy" else -qty
        realised = self._update_inventory(symbol, qty, price) - fee
        self.daily_pnl += realised
        self._maybe_snapshot(price)
        mtm = sum(q * (price - p) for q, p in self.lots.get(symbol, []))
        trade = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "side": side,
            "notional": notional,
            "price": price,
            "fee": fee,
            "slip": slip,
            "realised": realised,
            "mtm": mtm,
        }
        self.trades.append(trade)
        return realised, mtm

    def _maybe_snapshot(self, price: float) -> None:
        now = datetime.now(timezone.utc)
        if now.date() != self._last_snapshot:
            total_realised = sum(self.realised.values())
            total_mtm = sum(
                q * (price - p)
                for lots in self.lots.values()
                for q, p in lots
            )
            row = {
                "date": self._last_snapshot.isoformat(),
                "realised": round(total_realised, 4),
                "mtm": round(total_mtm, 4),
            }
            pd.DataFrame([row]).to_csv(
                DAILY_PATH, mode="a", header=not os.path.exists(DAILY_PATH), index=False
            )
            self._last_snapshot = now.date()

_risk = RiskManager()


def check_risk(order: dict) -> bool:
    return _risk.check_risk(order["symbol"], order["side"], order["size_usd"])


def record_fill(symbol: str, side: str, notional: float, price: float, fee: float, slip: float) -> tuple[float, float]:
    return _risk.record_fill(symbol, side, notional, price, fee, slip)


def gross(symbol: str) -> float:
    return _risk.gross(symbol)


def daily_pnl() -> float:
    return _risk.daily_pnl


def last_trades(seconds: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc).timestamp() - seconds
    return [t for t in _risk.trades if datetime.fromisoformat(t["timestamp"]).timestamp() >= cutoff]


def total_mtm() -> float:
    tot = 0.0
    for sym, lots in _risk.lots.items():
        price = fetch_price(sym)
        tot += sum(q * (price - p) for q, p in lots)
    return tot
