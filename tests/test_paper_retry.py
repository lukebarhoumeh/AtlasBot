import importlib

import requests

import atlasbot.execution.paper as paper_mod


class FakeResp:
    def __init__(self, status: int, data=None):
        self.status_code = status
        self._data = data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()

    def json(self):
        return self._data


def test_paper_order_ok(monkeypatch):
    paper = importlib.reload(paper_mod)
    monkeypatch.setenv("COINBASE_PAPER_KEY", "x")
    monkeypatch.setattr(paper, "fetch_price", lambda s: 100.0)
    monkeypatch.setattr(
        paper.requests,
        "post",
        lambda *a, **k: FakeResp(
            200, {"order_id": "ok", "average_filled_price": "100", "filled_size": "1"}
        ),
    )
    fill = paper.submit_order("buy", 100, "BTC-USD")
    assert fill.order_id == "ok"


def test_paper_order_fail(monkeypatch):
    paper = importlib.reload(paper_mod)
    monkeypatch.setenv("COINBASE_PAPER_KEY", "x")
    monkeypatch.setattr(paper, "fetch_price", lambda s: 100.0)
    calls = []

    def bad_post(*a, **k):
        calls.append(1)
        return FakeResp(500)

    monkeypatch.setattr(paper.requests, "post", bad_post)
    monkeypatch.setattr(paper.time, "sleep", lambda s: None)
    fill = paper.submit_order("buy", 100, "BTC-USD")
    assert fill.order_id == "paper-error"
    assert len(calls) >= 3
