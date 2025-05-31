import importlib


def test_cycle_env(monkeypatch):
    monkeypatch.setenv("CYCLE_SEC", "0.1")
    rb = importlib.import_module("cli.run_bot")
    loops = 0

    def _once(*a, **k):
        nonlocal loops
        loops += 1
        return False

    monkeypatch.setattr(rb, "_run_once", _once)
    rb.main(simulate=True, max_loops=30)
    assert loops >= 25
