from __future__ import annotations

import gzip
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from atlasbot.config import (
    FEE_MIN_USD,
    MAX_DAILY_LOSS,
    MAX_GROSS_USD,
    START_CASH,
    TAKER_FEE,
)
from atlasbot.utils import fetch_price

PNL_PATH = "data/logs/pnl.csv"
DAILY_PATH = "data/logs/daily_pnl.csv"
SUMMARY_PATH = Path(os.getenv("LOG_DIR", "logs")).joinpath("pnl_summary.jsonl")


class RiskManager:
    def __init__(self, starting_cash: float = START_CASH):
        self.lots: dict[str, list[tuple[float, float]]] = {}
        self.realised = {}
        self.daily_pnl = 0.0
        self.cash = starting_cash
        self.equity = starting_cash
        self.free_margin = starting_cash
        self.day_start_equity = starting_cash
        self._last_snapshot = datetime.now(timezone.utc)
        self.trades: list[dict] = []
        self.stats: dict[str, dict] = {}
        self.open_fees: dict[str, float] = {}
        self._lock = threading.Lock()
        self._ledger_idx = 0
        self.maker_fills = 0
        self.taker_fills = 0
        self.day_trades = 0
        threading.Thread(target=self._ledger_loop, daemon=True).start()

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
        with self._lock:
            return sum(abs(q) * p for q, p in self.lots.get(symbol, []))

    def check_risk(self, symbol: str, side: str, size_usd: float) -> bool:
        with self._lock:
            pos = sum(abs(q) * p for q, p in self.lots.get(symbol, []))
            new_pos = pos + size_usd if side == "buy" else pos - size_usd
            if abs(new_pos) > MAX_GROSS_USD:
                return False
            if self.daily_pnl <= -MAX_DAILY_LOSS:
                return False
            est_fee = max(size_usd * TAKER_FEE, FEE_MIN_USD)
            if side == "buy" and size_usd + est_fee > self.free_margin:
                return False
            return True

    def record_fill(
        self,
        symbol: str,
        side: str,
        notional: float,
        price: float,
        fee: float,
        slip: float,
        maker: bool = False,
    ) -> tuple[float, float]:
        with self._lock:
            qty = notional / price
            qty = qty if side == "buy" else -qty
            realised = self._update_inventory(symbol, qty, price)
            pnl = 0.0
            if realised == 0:
                self.open_fees[symbol] = self.open_fees.get(symbol, 0.0) + fee
            else:
                fee += self.open_fees.pop(symbol, 0.0)
                pnl = realised - fee
                self.daily_pnl += pnl
            if side == "buy":
                self.cash -= notional + fee
            else:
                self.cash += notional - fee
            mtm = sum(q * (price - p) for q, p in self.lots.get(symbol, []))
            unrealised_total = 0.0
            for sym, lots in self.lots.items():
                try:
                    cur_px = fetch_price(sym)
                except RuntimeError:
                    cur_px = price
                unrealised_total += sum(q * (cur_px - p) for q, p in lots)
            self.equity = self.cash + unrealised_total
            self.free_margin = self.cash
            self._maybe_snapshot()
            trade = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": side,
                "notional": notional,
                "price": price,
                "fee": fee,
                "slip": slip,
                "realised": pnl,
                "mtm": mtm,
                "maker": maker,
            }
            self.trades.append(trade)

            if maker:
                self.maker_fills += 1
            else:
                self.taker_fills += 1
            if self._last_snapshot.date() != datetime.now(timezone.utc).date():
                self.day_trades = 0
            self.day_trades += 1

            st = self.stats.setdefault(
                symbol,
                {"realised": 0.0, "fees": 0.0, "slip": 0.0, "trades": 0, "gross": 0.0},
            )
            st["realised"] += pnl
            st["fees"] += fee
            st["slip"] += slip
            st["trades"] += 1
            st["gross"] = st["realised"] + st["fees"] + st["slip"]
            return pnl, mtm

    def _maybe_snapshot(self) -> None:
        now = datetime.now(timezone.utc)
        if now.date() != self._last_snapshot.date():
            self.day_start_equity = self.equity
        if now - self._last_snapshot >= timedelta(minutes=5):
            row = self._summary_row(now)
            SUMMARY_PATH.parent.mkdir(exist_ok=True)
            with open(SUMMARY_PATH, "a") as f:
                f.write(json.dumps(row) + "\n")
            self._last_snapshot = now

    def _ledger_loop(self) -> None:
        while True:
            self._snapshot_ledger()
            self._gzip_old_ledgers(Path("data"))
            time.sleep(60)

    def _snapshot_ledger(self) -> None:
        path = Path(f"data/ledger_{datetime.now(timezone.utc):%Y-%m-%d}.jsonl")
        path.parent.mkdir(exist_ok=True)
        with self._lock:
            new_trades = self.trades[self._ledger_idx :]
            self._ledger_idx = len(self.trades)
        if not new_trades:
            return
        with open(path, "a") as f:
            for t in new_trades:
                f.write(json.dumps(t) + "\n")

    def _gzip_old_ledgers(self, root: Path) -> None:
        cutoff = time.time() - 86_400
        for p in root.glob("ledger_*.jsonl"):
            try:
                if (
                    p.stat().st_mtime < cutoff
                    and not p.with_suffix(p.suffix + ".gz").exists()
                ):
                    with open(p, "rb") as src, gzip.open(
                        p.with_suffix(p.suffix + ".gz"), "wb"
                    ) as dst:
                        dst.write(src.read())
                    os.remove(p)
            except FileNotFoundError:
                continue

    def _summary_row(self, now: datetime) -> dict:
        total_realised = sum(self.realised.values())
        total_mtm = 0.0
        row: dict[str, float | str] = {
            "ts": now.isoformat(),
            "equity": 0.0,
            "cash": round(self.cash, 4),
            "realised": round(total_realised, 4),
            "fees": round(sum(t["fee"] for t in self.trades), 4),
            "slip": round(sum(t["slip"] for t in self.trades), 4),
            "mtm": 0.0,
        }
        for sym, lots in self.lots.items():
            try:
                px = fetch_price(sym)
            except RuntimeError:
                px = 0.0
            mtm = sum(q * (px - p) for q, p in lots)
            total_mtm += mtm
            pos = sum(q for q, _ in lots)
            tag = sym.split("-")[0]
            row[f"{tag}.net"] = round(self.realised.get(sym, 0.0) + mtm, 4)
            row[f"{tag}.size"] = round(pos, 8)
        row["equity"] = round(self.cash + total_mtm, 4)
        row["mtm"] = round(total_mtm, 4)
        return row


_risk = RiskManager()


def portfolio_snapshot() -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    unreal_total = 0.0
    per_symbol: dict[str, dict] = {}
    for sym, lots in _risk.lots.items():
        try:
            px = fetch_price(sym)
        except RuntimeError:
            px = 0.0
        mtm = sum(q * (px - p) for q, p in lots)
        pos = sum(q for q, _ in lots)
        per_symbol[sym] = {
            "pos": round(pos, 8),
            "mtm": round(mtm, 4),
            "realised": round(_risk.realised.get(sym, 0.0), 4),
        }
        unreal_total += mtm
    fees = sum(t["fee"] for t in _risk.trades)
    slippage = sum(t["slip"] for t in _risk.trades)
    snap = {
        "timestamp": ts,
        "equity_usd": round(_risk.cash + unreal_total, 4),
        "cash_usd": round(_risk.cash, 4),
        "unreal_mtm_usd": round(unreal_total, 4),
        "fees_usd": round(fees, 4),
        "slippage_usd": round(slippage, 4),
        "per_symbol": per_symbol,
    }
    return snap


def check_risk(order: dict) -> bool:
    return _risk.check_risk(order["symbol"], order["side"], order["size_usd"])


def record_fill(
    symbol: str,
    side: str,
    notional: float,
    price: float,
    fee: float,
    slip: float,
    maker: bool = False,
) -> tuple[float, float]:
    return _risk.record_fill(symbol, side, notional, price, fee, slip, maker)


def gross(symbol: str) -> float:
    return _risk.gross(symbol)


def daily_pnl() -> float:
    return _risk.daily_pnl


def maker_fill_ratio() -> float:
    total = _risk.maker_fills + _risk.taker_fills
    return _risk.maker_fills / total if total else 0.0


_macro_hits = 0
_macro_total = 0


def record_macro_hit(hit: bool) -> None:
    global _macro_hits, _macro_total
    _macro_total += 1
    if hit:
        _macro_hits += 1


def macro_hit_rate() -> float:
    return _macro_hits / _macro_total if _macro_total else 0.0


def trade_count_day() -> int:
    return _risk.day_trades


def last_trades(seconds: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc).timestamp() - seconds
    return [
        t
        for t in _risk.trades
        if datetime.fromisoformat(t["timestamp"]).timestamp() >= cutoff
    ]


def last_fills(n: int = 200) -> list[dict]:
    return _risk.trades[-n:]


def annotate_last_trade(**extra) -> None:
    if _risk.trades:
        _risk.trades[-1].update(extra)


def total_mtm() -> float:
    tot = 0.0
    for sym, lots in _risk.lots.items():
        price = fetch_price(sym)
        tot += sum(q * (price - p) for q, p in lots)
    return tot


def cash() -> float:
    return _risk.cash


def equity() -> float:
    return _risk.equity


def snapshot() -> None:
    _risk._maybe_snapshot()


def summary_row() -> dict:
    return _risk._summary_row(datetime.now(timezone.utc))


_circuit_until = 0.0


def check_circuit_breaker() -> bool:
    """Return True if daily loss exceeds 2% and circuit is engaged."""
    global _circuit_until
    now = time.time()
    if now < _circuit_until:
        return True
    start_eq = _risk.day_start_equity
    if start_eq and (_risk.equity - start_eq) / start_eq <= -0.02:
        _circuit_until = now + 3600
        return True
    return False


def circuit_breaker_active() -> bool:
    """True if the circuit breaker is currently active."""
    return time.time() < _circuit_until
