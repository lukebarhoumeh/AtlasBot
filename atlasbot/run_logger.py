"""Run-scoped CSV trade ledger."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

RUN_DIR = REPO_ROOT / "data" / "runs"
RUN_DIR.mkdir(parents=True, exist_ok=True)
RUN_CSV = RUN_DIR / f"ledger_{datetime.now(timezone.utc):%Y-%m-%d_%H-%M-%S}.csv"
DECISIONS_CSV = (
    REPO_ROOT / "logs" / f"decisions_{datetime.now(timezone.utc):%Y-%m-%d}.csv"
)


def _safe_sync(paths: Sequence[Path]) -> None:
    """Safely sync *paths* to disk cross-platform.

    Args:
        paths: File paths whose contents should be flushed to disk.
    """
    if hasattr(os, "sync"):
        os.sync()
    else:
        for p in paths:
            if p.exists():
                with open(p, "rb") as fh:
                    os.fsync(fh.fileno())


def append(row: dict) -> None:
    """Append *row* to the run ledger CSV."""
    header = not RUN_CSV.exists()
    RUN_CSV.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row])
    df.to_csv(RUN_CSV, mode="a", header=header, index=False)
    _safe_sync([RUN_CSV, DECISIONS_CSV])


def log_decision(row: dict) -> None:
    """Append decision *row* to the daily CSV ledger."""
    header = not DECISIONS_CSV.exists()
    DECISIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row])
    df.to_csv(DECISIONS_CSV, mode="a", header=header, index=False)
    _safe_sync([RUN_CSV, DECISIONS_CSV])
