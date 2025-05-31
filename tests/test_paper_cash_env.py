import importlib

import atlasbot.config as cfg
import atlasbot.risk as risk


def test_paper_cash_env(monkeypatch):
    monkeypatch.setenv("PAPER_CASH", "12345")
    importlib.reload(cfg)
    importlib.reload(risk)
    assert risk.cash() == 12345.0
