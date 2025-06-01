import pytest

import atlasbot.utils as utils


def test_ensure_ready_ci(monkeypatch, caplog):
    monkeypatch.setenv("CI", "true")
    caplog.set_level("WARNING")
    utils._ensure_ready()
    assert any("skipping market-data" in rec.message for rec in caplog.records)


def test_ensure_ready_retries(monkeypatch):
    calls = []

    class Dummy:
        mode = "test"

        def wait_ready(self, timeout=15):
            calls.append(timeout)
            return False

    monkeypatch.setenv("CI", "false")
    monkeypatch.setattr(utils, "_get_md", lambda: Dummy())
    with pytest.raises(RuntimeError):
        utils._ensure_ready(0)
    assert len(calls) == 3
