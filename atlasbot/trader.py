import time
import asyncio
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd

from atlasbot.utils import fetch_price, calculate_atr, fetch_volatility
from atlasbot.gpt_report import GPTTrendAnalyzer
from atlasbot.decision_engine import DecisionEngine
from atlasbot.execution import get_backend
from atlasbot.config import (
    LOG_PATH as TRADE_LOG_PATH,
    PROFIT_TARGETS,
    MAX_NOTIONAL_USD,
    EXECUTION_BACKEND,
    DESK_SUMMARY_S,
)
from atlasbot import risk
from atlasbot.ai_desk import AIDesk, LOG_PATH as DESK_LOG_PATH
from atlasbot.secrets_loader import get_openai_api_key


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
        log_file: str = TRADE_LOG_PATH,
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
                atr=atr,
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
        atr: float,
        timeout_s: int = 300,
    ) -> tuple[float, int]:
        """TP / SL / max-hold simulation loop."""
        tp = entry_price * (1 + profit_target_pct) if side == "buy" else entry_price * (
            1 - profit_target_pct
        )
        sl_pt = entry_price * (1 - profit_target_pct) if side == "buy" else entry_price * (
            1 + profit_target_pct
        )
        sl_atr = entry_price - 2 * atr if side == "buy" else entry_price + 2 * atr
        sl = min(sl_pt, sl_atr) if side == "buy" else max(sl_pt, sl_atr)

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
        self.pnl_file = pnl_file
        try:
            asyncio.get_running_loop().create_task(desk_runner())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_until_complete, args=(desk_runner(),), daemon=True).start()

    # --------------------------------------------------------------- main loop
    def run_cycle(self) -> None:
        for symbol in PROFIT_TARGETS:
            advice = self.engine.next_advice(symbol)
            side = "buy" if advice["bias"] == "long" else "sell"
            size_usd = 10 * advice["confidence"]
            order = {"symbol": symbol, "side": side, "size_usd": size_usd}
            if not risk.check_risk(order):
                continue
            self.exec.submit_order(side, size_usd, symbol)


async def desk_runner():
    if not get_openai_api_key():
        logging.info("[GPT disabled] no OPENAI_API_KEY")
        return
    desk = AIDesk()
    interval = desk.ttl
    while True:
        await asyncio.sleep(interval)
        trades = risk.last_trades(interval)
        if not trades:
            logging.info("[GPT desk] No recent trades")
            continue
        try:
            summ = await desk.summarize(trades)
            if not summ:
                continue
            logging.info("[GPT] %s", summ.get("summary", ""))
            DESK_LOG_PATH.parent.mkdir(exist_ok=True)
            with open(DESK_LOG_PATH, "a") as f:
                f.write(summ.get("summary", "") + "\n")
        except Exception as exc:  # noqa: BLE001
            logging.error("desk_runner: %s", exc)

