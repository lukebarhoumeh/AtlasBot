import atlasbot.decision_engine as de


def test_adaptive_weights(monkeypatch):
    engine = de.DecisionEngine()
    trades = [
        {"signals": {"orderflow": 1, "momentum": 0, "macro": 0}, "return": 1}
        for _ in range(10)
    ]
    monkeypatch.setattr(de.risk, "last_fills", lambda n=200: trades)
    engine._adapt_weights()
    assert engine.weights["orderflow"] > engine.weights["momentum"]
