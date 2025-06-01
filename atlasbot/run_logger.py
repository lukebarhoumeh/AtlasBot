"""Run-scoped CSV trade ledger."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd

# ──────────────────────────── paths ──────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent

RUN_DIR = REPO_ROOT / "data" / "runs"
RUN_DIR.mkdir(parents=True, exist_ok=True)

RUN_CSV = RUN_DIR / f"ledger_{datetime.now(timezone.utc):%Y-%m-%d_%H-%M-%S}.csv"
DECISIONS_CSV = REPO_ROOT / "logs" / f"decisions_{datetime.now(timezone.utc):%Y-%m-%d}.csv"


# ────────────────────────── helpers ──────────────────────────────
def _safe_sync(paths: Sequence[Path]) -> None:
    """Flush *paths* to disk on any OS.

    POSIX  : call ``os.sync()`` (flushes all dirty buffers).
    Windows: open each file in append-binary mode, flush + fsync.
    Silently ignores fsync errors on readonly handles (EBADF).
    """
    if hasattr(os, "sync"):                # Linux / macOS fast-path
        os.sync()
        return

    for p in paths:
        if not p.exists():
            continue
        try:
            # open for append so Windows allows fsync
            with open(p, "ab", buffering=0) as fh:
                fh.flush()
                os.fsync(fh.fileno())
        except (OSError, AttributeError):
            # Windows may raise EBADF or fsync may be absent—safe to ignore
            pass


# ───────────────────────── CSV writers ───────────────────────────
def append(row: dict) -> None:
    """Append a *row* to the per-run ledger CSV."""
    header = not RUN_CSV.exists()
    RUN_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(RUN_CSV, mode="a", header=header, index=False)
    _safe_sync([RUN_CSV, DECISIONS_CSV])


def log_decision(row: dict) -> None:
    """Append a decision *row* to the daily decision CSV."""
    header = not DECISIONS_CSV.exists()
    DECISIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(DECISIONS_CSV, mode="a", header=header, index=False)
    _safe_sync([RUN_CSV, DECISIONS_CSV])
