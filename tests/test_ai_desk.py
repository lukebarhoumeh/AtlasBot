import asyncio
import asyncio
import logging
from types import SimpleNamespace
import openai

from atlasbot.ai_desk import AIDesk, LOG_PATH


def test_ai_summary_bad_json(monkeypatch, caplog):
    bad = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{"))])
    monkeypatch.setattr(openai.chat.completions, "create", lambda *a, **k: bad)
    monkeypatch.setattr(openai, "api_key", "x")
    caplog.set_level(logging.WARNING)
    out = asyncio.run(AIDesk().summarize([{"t":1}]))
    assert out == {}
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_ai_summary_good(monkeypatch, tmp_path):
    good = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"hi","score":0.1,"next_action":"flat"}'))])
    monkeypatch.setattr(openai.chat.completions, "create", lambda *a, **k: good)
    monkeypatch.setattr(openai, "api_key", "x")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    res = asyncio.run(AIDesk().summarize([{"t":1}]))
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(res.get("summary", "") + "\n")
    assert LOG_PATH.exists()
    assert "hi" in LOG_PATH.read_text()
