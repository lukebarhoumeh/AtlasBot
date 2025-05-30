from atlasbot.decision_engine import DecisionEngine


class FakeSignals:
    def __init__(self, i, m, a):
        self.i = i
        self.m = m
        self.a = a

    def imbalance(self, s):
        return self.i

    def momentum(self, s):
        return self.m

    def macro_bias(self, s):
        return self.a


def test_weighted_output(monkeypatch):
    de = DecisionEngine()
    import atlasbot.signals as sig

    monkeypatch.setattr(sig, "imbalance", lambda s: 0.5)
    monkeypatch.setattr(sig, "momentum", lambda s: 0.5)
    monkeypatch.setattr(sig, "macro_bias", lambda s: 0.5)
    adv = de.next_advice("BTC-USD")
    assert adv["bias"] in {"long", "short", "flat"}
    assert 0 <= adv["confidence"] <= 1.5
