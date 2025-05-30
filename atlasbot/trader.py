import asyncio
import logging
import math
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

import atlasbot.config as cfg
from atlasbot import metrics, risk
from atlasbot.ai_desk import LOG_PATH as DESK_LOG_PATH
from atlasbot.ai_desk import AIDesk
from atlasbot.config import LOG_PATH as TRADE_LOG_PATH
from atlasbot.config import profit_target
from atlasbot.decision_engine import DecisionEngine
from atlasbot.execution import get_backend
from atlasbot.gpt_report import GPTTrendAnalyzer
from atlasbot.market_data import get_market
from atlasbot.secrets_loader import get_openai_api_key
from atlasbot.utils import calculate_atr, fetch_price, fetch_volatility

SYMBOLS = cfg.SYMBOLS


class TradingBot:
    """
    Live-price, volatility-scaled, GPT-filtered *sim* trader.

    Replace `_simulate_trade()` with real order placement when ready.
    """

    # ----------------------------------------------------------------- life-cycle
    def __init__(
        self,
        symbols: list[str] = cfg.SYMBOLS,
        max_notional_usd: Optional[float] = None,
        gpt_trend_analyzer: Optional[GPTTrendAnalyzer] = None,
        log_file: str = TRADE_LOG_PATH,
    ):
        self.symbols = symbols
        self.max_notional_usd = max_notional_usd or cfg.MAX_NOTIONAL_USD
        self.gpt = gpt_trend_analyzer or GPTTrendAnalyzer(enabled=False)
        self.log_file = log_file
        self._skip_logged: set[str] = set()

    # ----------------------------------------------------------------- public API
    def run_cycle(self) -> None:
        """Iterate once over every configured symbol."""
        utc_now = datetime.now(timezone.utc)

        for symbol in self.symbols:
            price = fetch_price(symbol)

            atr = calculate_atr(symbol)
            vol = fetch_volatility(symbol)
            if math.isnan(atr) or math.isnan(vol):
                if symbol not in self._skip_logged:
                    logging.debug(
                        "[SKIP] %s waiting for bars (have=%d)",
                        symbol,
                        len(get_market().minute_bars(symbol)),
                    )
                    self._skip_logged.add(symbol)
                continue
            self._skip_logged.discard(symbol)

            pt_pct = profit_target(symbol)

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
        timeout_s: int | None = None,
    ) -> tuple[float, int]:
        """TP / SL / max-hold simulation loop."""
        if timeout_s is None:
            timeout_s = cfg.MAX_HOLD_MIN * 60
        tp = (
            entry_price * (1 + profit_target_pct)
            if side == "buy"
            else entry_price * (1 - profit_target_pct)
        )
        sl_pt = (
            entry_price * (1 - profit_target_pct)
            if side == "buy"
            else entry_price * (1 + profit_target_pct)
        )
        sl_atr = entry_price - 2 * atr if side == "buy" else entry_price + 2 * atr
        sl = min(sl_pt, sl_atr) if side == "buy" else max(sl_pt, sl_atr)

        start = time.time()
        while True:
            cur_price = fetch_price(symbol)

            hit_tp = (
                side == "buy" and cur_price >= tp or side == "sell" and cur_price <= tp
            )
            hit_sl = (
                side == "buy" and cur_price <= sl or side == "sell" and cur_price >= sl
            )
            timed_out = time.time() - start >= timeout_s

            if hit_tp or hit_sl or timed_out:
                return cur_price, int(time.time() - start)

            time.sleep(1)

    # -------------------------------------- persistence / console
    def _log_trade(self, trade: dict) -> None:
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

    def __init__(
        self,
        decision_engine: DecisionEngine | None = None,
        backend: str = cfg.EXECUTION_BACKEND,
        pnl_file: str = "data/logs/pnl.csv",
    ):
        self.engine = decision_engine or DecisionEngine()
        self.backend_name = backend
        self.exec = get_backend(backend)
        self.pnl_file = pnl_file
        self._skip_logged: set[str] = set()
        self._conflict_counts: dict[str, int] = {}
        try:
            asyncio.get_running_loop().create_task(desk_runner())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            threading.Thread(
                target=loop.run_until_complete, args=(desk_runner(),), daemon=True
            ).start()

    # --------------------------------------------------------------- main loop
    def run_cycle(self) -> None:
        md = get_market()
        if risk.check_circuit_breaker():
            if self.backend_name != "sim":
                logging.warning("Circuit breaker engaged – using sim backend")
            self.exec = get_backend("sim")
        else:
            self.exec = get_backend(self.backend_name)
        for symbol in cfg.SYMBOLS:
            advice = self.engine.next_advice(symbol)
            if advice["bias"] == "flat":
                continue
            im = advice.get("rationale", {}).get("orderflow", 0.0)
            mo = advice.get("rationale", {}).get("momentum", 0.0)
            if im * mo < 0 and abs(im) > cfg.CONFLICT_THRESH:
                cnt = self._conflict_counts.get(symbol, 0) + 1
                self._conflict_counts[symbol] = cnt
                if not cfg.ALLOW_CONFLICT:
                    continue
                risk.annotate_last_trade(conflict=True)
            else:
                self._conflict_counts[symbol] = 0
            edge_bps = abs(advice.get("edge", 0.0) * 10_000)
            metrics.edge_g.set(edge_bps)
            metrics.edge_hist.observe(edge_bps)
            if edge_bps <= cfg.FEE_BPS + cfg.SLIPPAGE_BPS + cfg.MIN_EDGE_BPS:
                continue
            side = "buy" if advice["bias"] == "long" else "sell"
            price = fetch_price(symbol)
            atr = calculate_atr(symbol)
            if math.isnan(atr):
                if symbol not in self._skip_logged:
                    logging.debug(
                        "[SKIP] %s waiting for bars (have=%d)",
                        symbol,
                        len(md.minute_bars(symbol)),
                    )
                    self._skip_logged.add(symbol)
                continue
            self._skip_logged.discard(symbol)
            equity = risk.equity()
            conf = max(advice.get("confidence", 0.0), 0.0)
            size_usd = equity * cfg.RISK_PER_TRADE * conf / (atr / price if atr else 1)
            if risk.trade_count_day() > 100:
                size_usd *= 0.75
            order = {
                "symbol": symbol,
                "side": side,
                "size_usd": size_usd,
                "take_profit": price * (1 + advice.get("edge", 0.0)),
            }
            if not risk.check_risk(order):
                continue
            filled = None
            if cfg.EXECUTION_MODE == "maker":
                for _ in range(3):
                    if hasattr(self.exec, "submit_maker_order"):
                        filled = self.exec.submit_maker_order(side, size_usd, symbol)
                    if filled:
                        break
                    time.sleep(1)
                if not filled:
                    filled = self.exec.submit_order(side, size_usd, symbol)
            else:
                filled = self.exec.submit_order(side, size_usd, symbol)
            if filled:
                self._exit_position(symbol, side, filled.qty, filled.price, atr)
            risk.annotate_last_trade(signals=advice["rationale"], ret=0.0)
            mbias = advice.get("rationale", {}).get("macro", 0.0)
            hit = (side == "buy" and mbias > 0) or (side == "sell" and mbias < 0)
            risk.record_macro_hit(hit)
            metrics.trade_count_day_g.set(risk.trade_count_day())

    # ---------------------------------------------------------------- exit logic
    def _exit_position(
        self, symbol: str, side: str, qty: float, entry: float, atr: float
    ) -> None:
        """Close position via ATR-based TP/SL or timeout."""
        tp = entry + cfg.K_TP * atr if side == "buy" else entry - cfg.K_TP * atr
        sl = entry - cfg.K_SL * atr if side == "buy" else entry + cfg.K_SL * atr
        end = time.time() + cfg.MAX_HOLD_MIN * 60
        exit_side = "sell" if side == "buy" else "buy"
        while True:
            px = fetch_price(symbol)
            if (side == "buy" and px >= tp) or (side == "sell" and px <= tp):
                metrics.exit_tp_total.inc()
                break
            if (side == "buy" and px <= sl) or (side == "sell" and px >= sl):
                metrics.exit_sl_total.inc()
                break
            if time.time() >= end:
                metrics.exit_timeout_total.inc()
                break
            time.sleep(1)
        self.exec.submit_order(exit_side, qty * px, symbol)


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
