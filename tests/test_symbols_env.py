import importlib

import atlasbot.config as cfg


def test_symbols_env(monkeypatch):
    monkeypatch.setenv("SYMBOLS", "BCH-USD,DOGE-USD")
    importlib.reload(cfg)
    assert cfg.SYMBOLS == ["BCH-USD", "DOGE-USD"]
