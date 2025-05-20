import time
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd

from utils import fetch_price, calculate_atr, fetch_volatility
from gpt_report import GPTTrendAnalyzer


class TradingBot:
    """
    Places simulated trades using live Coinbase prices.
    Replace `simulate_trade()` with real order placement when ready.
    """

    def __init__(
        self,
        profit_target_map: Dict[str, float],
        max_notional_usd: float,
        gpt_trend_analyzer: Optional[GPTTrendAnalyzer] = None,
        log_file: str = "sim_tradesOverNight.csv",
    ):
        self.profit_target_map = profit_target_map
        self.max_notional_usd = max_notional_usd
        self.gpt = gpt_trend_analyzer or GPTTrendAnalyzer(enabled=False)
        self.log_file = log_file

    # ---------------------------------------------------------------------- API
    def run_cycle(self):
        for symbol, pt_pct in self.profit_target_map.items():
            price = fetch_price(symbol)
            atr = calculate_atr(symbol)
            vol = fetch_volatility(symbol)

            # Sizing: inverse vol capped by max_notional
            usd_position = min(self.max_notional_usd, (1 / vol) * 100)
            qty = round(usd_position / price, 8)

            trend = self.gpt.get_trend_confidence(symbol)
            side = "buy" if trend in ("BULL", "NEUTRAL") else "sell"

            entry_time = datetime.now(timezone.utc)
            entry_price = price

            # ---------- simulate trade ----------
            exit_price, duration_s = self._simulate_trade(
                symbol=symbol,
                side=side,
                qty=qty,
                entry_price=entry_price,
                profit_target_pct=pt_pct,
            )
            # -------------------------------------

            pnl = (exit_price - entry_price) * qty * (1 if side == "buy" else -1)
            result = "WIN" if pnl > 0 else "LOSS"

            self._log_trade(
                dict(
                    ts=entry_time.isoformat(),
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl=round(pnl, 2),
                    result=result,
                    atr=atr,
                    vol=vol,
                    trend_confidence=trend,
                    duration_sec=duration_s,
                )
            )

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _simulate_trade(
        *,
        symbol: str,
        side: str,
        qty: float,
        entry_price: float,
        profit_target_pct: float,
        timeout_s: int = 300,
    ):
        """
        Simplistic simulation:
          – take-profit at profit_target_pct
          – stop-loss at same distance
          – otherwise close at timeout
        """
        tp = entry_price * (1 + profit_target_pct) if side == "buy" else entry_price * (
            1 - profit_target_pct
        )
        sl = entry_price * (1 - profit_target_pct) if side == "buy" else entry_price * (
            1 + profit_target_pct
        )

        start = time.time()
        while True:
            cur_price = fetch_price(symbol)
            if (side == "buy" and cur_price >= tp) or (side == "sell" and cur_price <= tp):
                return cur_price, int(time.time() - start)
            if (side == "buy" and cur_price <= sl) or (side == "sell" and cur_price >= sl):
                return cur_price, int(time.time() - start)
            if time.time() - start >= timeout_s:
                return cur_price, timeout_s
            time.sleep(1)

    # ----------------------------------------------- persistence / stdout
    def _log_trade(self, trade: Dict):
        msg = (
            f"[{trade['symbol']}] {trade['result']} PnL={trade['pnl']}$ "
            f"Trend={trade['trend_confidence']} Dur={trade['duration_sec']}s"
        )
        print(msg)
        pd.DataFrame([trade]).to_csv(
            self.log_file, mode="a", header=not self._csv_exists(), index=False
        )

    def _csv_exists(self) -> bool:
        try:
            with open(self.log_file, "r"):
                return True
        except FileNotFoundError:
            return False
