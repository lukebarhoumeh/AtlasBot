"""Runtime diagnostics helpers."""

from __future__ import annotations

import csv
import io
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Deque, Dict, List

import atlasbot.config as cfg
import atlasbot.risk as risk
from atlasbot.secrets_loader import get_coinbase_credentials, get_openai_api_key

_REJECTS: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=100))


def record_reject(
    filter_name: str, reason: str, edge_bps: float, **extra: object
) -> None:
    """Store a trade rejection event."""
    _REJECTS[filter_name].appendleft(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "edge_bps": edge_bps,
            **extra,
        }
    )


def last_rejects(filter_name: str, n: int = 10) -> List[dict]:
    """Return the most recent *n* rejections for *filter_name*."""
    return list(_REJECTS.get(filter_name, []))[:n]


def get_env_config() -> dict:
    """Return environment and config information."""
    env_keys = [
        "PAPER_CASH",
        "MAX_NOTIONAL",
        "MAX_GROSS_USD",
        "EXECUTION_MODE",
        "COINBASE_PAPER_KEY",
        "OPENAI_API_KEY",
    ]
    env = {k: os.getenv(k) for k in env_keys}
    creds = get_coinbase_credentials()
    env["COINBASE_API_NAME"] = creds.get("api_name")
    env["OPENAI_API_KEY"] = get_openai_api_key() or env.get("OPENAI_API_KEY")
    config = {
        "MAX_NOTIONAL": cfg.MAX_NOTIONAL,
        "MAX_GROSS_USD": cfg.MAX_GROSS_USD,
        "EXECUTION_MODE": cfg.EXECUTION_MODE,
        "FEE_BPS_MAKER": cfg.FEE_BPS_MAKER,
        "FEE_BPS_TAKER": cfg.FEE_BPS_TAKER,
        "SLIPPAGE_BPS": cfg.SLIPPAGE_BPS,
        "MIN_EDGE_BPS": cfg.MIN_EDGE_BPS,
        "CONFLICT_THRESH": cfg.CONFLICT_THRESH,
        "SYMBOLS": ",".join(cfg.SYMBOLS),
    }
    missing = [k for k, v in env.items() if not v]
    return {"env": env, "config": config, "missing": missing}


def gating_status() -> dict:
    """Return current gate states."""
    return {
        "circuit_breaker": risk.circuit_breaker_active(),
        "kill_switch": risk.kill_switch_triggered(),
    }


def summary_csv(n: int = 10) -> str:
    """Return CSV summary of config, gating and rejects."""
    info = get_env_config()
    gate = gating_status()

    def _csv(rows: List[dict]) -> str:
        if not rows:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        return buf.getvalue()

    config_rows = [{"key": k, "value": v} for k, v in info["config"].items()]
    gate_rows = [{"gate": k, "status": v} for k, v in gate.items()]
    reject_rows = []
    for name, dq in _REJECTS.items():
        for rec in list(dq)[:n]:
            reject_rows.append({"filter": name, **rec})
    parts = ["# CONFIG", _csv(config_rows), "# GATES", _csv(gate_rows)]
    if reject_rows:
        parts.extend(["# REJECTS", _csv(reject_rows)])
    return "\n".join(parts)


def main() -> None:  # pragma: no cover - CLI helper
    print(summary_csv())


if __name__ == "__main__":  # pragma: no cover
    main()
