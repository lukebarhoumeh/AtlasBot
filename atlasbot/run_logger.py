"""Run-scoped CSV trade ledger."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

import pandas as pd

RUN_DIR = REPO_ROOT / "data" / "runs"
RUN_DIR.mkdir(parents=True, exist_ok=True)
RUN_CSV = RUN_DIR / f"ledger_{datetime.now(timezone.utc):%Y-%m-%d_%H-%M-%S}.csv"


def append(row: dict) -> None:
    """Append *row* to the run ledger CSV."""
    header = not RUN_CSV.exists()
    RUN_CSV.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row])
    df.to_csv(RUN_CSV, mode="a", header=header, index=False)
    os.sync()
