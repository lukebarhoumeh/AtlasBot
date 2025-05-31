import importlib

import atlasbot.config as cfg


def test_min_edge_env(monkeypatch):
    monkeypatch.setenv("MIN_EDGE_BPS", "4")
    importlib.reload(cfg)
    assert cfg.MIN_EDGE_BPS == 4
