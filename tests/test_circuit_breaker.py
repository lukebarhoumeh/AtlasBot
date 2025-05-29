import importlib

import atlasbot.risk as risk_mod


def test_circuit_breaker(monkeypatch):
    risk = importlib.reload(risk_mod)
    risk._risk.equity = 98.0
    risk._risk.day_start_equity = 100.0
    monkeypatch.setattr(risk.time, "time", lambda: 1000.0)
    assert risk.check_circuit_breaker()
    assert risk.circuit_breaker_active()
    assert risk._circuit_until == 1000.0 + 3600
