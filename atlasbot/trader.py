import time
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd

from atlasbot.utils import fetch_price, calculate_atr, fetch_volatility
from atlasbot.gpt_report import GPTTrendAnalyzer
from atlasbot.decision_engine import DecisionEngine
from atlasbot.execution import get_backend
from atlasbot.config import (
    LOG_PATH,
    PROFIT_TARGETS,
    MAX_NOTIONAL_USD,
    EXECUTION_BACKEND,
)
from atlasbot import risk


class TradingBot:
    """
    Live-price, volatility-scaled, GPT-filtered *sim* trader.

    Replace `_simulate_trade()` with real order placement when ready.
    """

    # ----------------------------------------------------------------- life-cycle
    def __init__(
        self,
        profit_target_map: Optional[Dict[str, float]] = None,
        max_notional_usd: Optional[float] = None,
        gpt_trend_analyzer: Optional[GPTTrendAnalyzer] = None,
        log_file: str = LOG_PATH,
    ):
        self.profit_target_map = profit_target_map or PROFIT_TARGETS
        self.max_notional_usd = max_notional_usd or MAX_NOTIONAL_USD
        self.gpt = gpt_trend_analyzer or GPTTrendAnalyzer(enabled=False)
        self.log_file = log_file

    # ----------------------------------------------------------------- public API
    def run_cycle(self) -> None:
        """Iterate once over every symbol in the map."""
        utc_now = datetime.now(timezone.utc)  # single timestamp for consistency

        for symbol, pt_pct in self.profit_target_map.items():
            price = fetch_price(symbol)

            # --- data warm-up guard
            try:
                atr = calculate_atr(symbol)
                vol = fetch_volatility(symbol)
            except RuntimeError:
                print(f"[{symbol}] waiting for live data warm-up…")
                continue

            # --- position sizing
            usd_position = min(self.max_notional_usd, (1 / vol) * 100)
            qty = round(usd_position / price, 8)

            trend = self.gpt.get_trend_confidence(symbol)
            side = "buy" if trend in ("BULL", "NEUTRAL") else "sell"

            # ---------- simulate trade ----------
            exit_price, duration_s = self._simulate_trade(
                symbol=symbol,
                side=side,
                qty=qty,
                entry_price=price,
                profit_target_pct=pt_pct,
            )
            # -------------------------------------

            pnl = (exit_price - price) * qty * (1 if side == "buy" else -1)
            result = "WIN" if pnl > 0 else "LOSS"

            self._log_trade(
                dict(
                    ts=utc_now.isoformat(),
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    entry_price=price,
                    exit_price=exit_price,
                    pnl=round(pnl, 2),
                    result=result,
                    atr=atr,
                    vol=vol,
                    trend_confidence=trend,
                    duration_sec=duration_s,
                )
            )

    # ----------------------------------------------------------------- internals
    @staticmethod
    def _simulate_trade(
        *,
        symbol: str,
        side: str,
        qty: float,
        entry_price: float,
        profit_target_pct: float,
        timeout_s: int = 300,
    ) -> tuple[float, int]:
        """TP / SL / max-hold simulation loop."""
        tp = entry_price * (1 + profit_target_pct) if side == "buy" else entry_price * (
            1 - profit_target_pct
        )
        sl = entry_price * (1 - profit_target_pct) if side == "buy" else entry_price * (
            1 + profit_target_pct
        )

        start = time.time()
        while True:
            cur_price = fetch_price(symbol)

            hit_tp = side == "buy" and cur_price >= tp or side == "sell" and cur_price <= tp
            hit_sl = side == "buy" and cur_price <= sl or side == "sell" and cur_price >= sl
            timed_out = time.time() - start >= timeout_s

            if hit_tp or hit_sl or timed_out:
                return cur_price, int(time.time() - start)

            time.sleep(1)

    # -------------------------------------- persistence / console
    def _log_trade(self, trade: Dict) -> None:
        print(
            f"[{trade['symbol']}] {trade['result']} "
            f"PnL={trade['pnl']}$ Trend={trade['trend_confidence']} "
            f"Dur={trade['duration_sec']}s"
        )
        pd.DataFrame([trade]).to_csv(
            self.log_file, mode="a", header=not self._csv_exists(), index=False
        )

    def _csv_exists(self) -> bool:
        try:
            with open(self.log_file, "r"):
                return True
        except FileNotFoundError:
            return False


class IntradayTrader:
    """Alpha-driven trader with risk and PnL tracking."""

    def __init__(self, decision_engine: DecisionEngine | None = None, backend: str = EXECUTION_BACKEND,
                 pnl_file: str = "data/logs/pnl.csv"):
        self.engine = decision_engine or DecisionEngine()
        self.exec = get_backend(backend)
        self.positions: Dict[str, list[tuple[float, float]]] = {s: [] for s in PROFIT_TARGETS}
        self.realised = {s: 0.0 for s in PROFIT_TARGETS}
        self.pnl_file = pnl_file
        self._last_pnl_print = time.time()

    # --------------------------------------------------------------- main loop
    def run_cycle(self) -> None:
        for symbol in PROFIT_TARGETS:
            advice = self.engine.next_advice(symbol)
            side = "buy" if advice["bias"] == "long" else "sell"
            size_usd = 10 * advice["confidence"]
            order = {"symbol": symbol, "side": side, "size_usd": size_usd}
            if not risk.check_risk(order):
                continue
            exec_id, qty, price = self.exec.submit_order(side, size_usd, symbol)
            delta = qty * price if side == "buy" else -qty * price
            realised = self._update_inventory(symbol, qty if side == "buy" else -qty, price)
            risk.update_position(symbol, delta)
            risk.add_pnl(realised)
        if time.time() - self._last_pnl_print >= 300:
            self._log_pnl()
            self._last_pnl_print = time.time()

    # --------------------------------------------------------------- inventory
    def _update_inventory(self, symbol: str, qty: float, price: float) -> float:
        lots = self.positions[symbol]
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
        self.realised[symbol] += realised
        return realised

    def _log_pnl(self) -> None:
        rows = []
        ts = datetime.utcnow().isoformat()
        for sym, lots in self.positions.items():
            qty = sum(q for q, _ in lots)
            avg_price = sum(q * p for q, p in lots) / qty if qty else 0.0
            mtm = qty * (fetch_price(sym) - avg_price)
            row = {
                "ts": ts,
                "symbol": sym,
                "pos": qty,
                "avg_price": avg_price,
                "mtm": mtm,
                "realised": self.realised[sym],
            }
            rows.append(row)
        pd.DataFrame(rows).to_csv(self.pnl_file, mode="a", header=not self._csv_exists2(), index=False)

    def _csv_exists2(self) -> bool:
        try:
            with open(self.pnl_file, "r"):
                return True
        except FileNotFoundError:
            return False
