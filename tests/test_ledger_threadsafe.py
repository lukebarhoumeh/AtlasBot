import concurrent.futures
import importlib

import atlasbot.risk as risk_mod


def test_ledger_threadsafe(monkeypatch):
    risk = importlib.reload(risk_mod)
    monkeypatch.setattr(risk, "fetch_price", lambda s: 100.0)

    def worker():
        risk.record_fill("BTC-USD", "buy", 100, 100, 0.1, 0.0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for _ in range(1000):
            ex.submit(worker)
    assert len(risk._risk.trades) == 1000
