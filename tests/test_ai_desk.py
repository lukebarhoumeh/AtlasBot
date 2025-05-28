import asyncio
import logging
from types import SimpleNamespace
import importlib

from atlasbot import ai_desk


def test_ai_summary_bad_json(monkeypatch, caplog):
    bad = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{"))])
    monkeypatch.setattr(ai_desk.client.chat.completions, "create", lambda *a, **k: bad)
    ai_desk.client.api_key = "x"
    caplog.set_level(logging.WARNING)
    out = ai_desk._safe_chat("hi", model="gpt", retries=(0, 0))
    assert out["bias"] == "neutral"
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_ai_summary_good(monkeypatch, tmp_path):
    good = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"bias":"long","confidence":1,"headline":"ok"}'))])
    monkeypatch.setattr(ai_desk.client.chat.completions, "create", lambda *a, **k: good)
    ai_desk.client.api_key = "x"
    monkeypatch.setenv("AI_ADVISOR_LOG", str(tmp_path/"ai.log"))
    importlib.reload(ai_desk)
    monkeypatch.setattr(ai_desk.client.chat.completions, "create", lambda *a, **k: good)
    ai_desk.client.api_key = "x"
    res = ai_desk._safe_chat("hi", model="gpt", retries=(0,))
    ai_desk.LOG_PATH.parent.mkdir(exist_ok=True)
    with open(ai_desk.LOG_PATH, "a") as f:
        f.write(res.get("headline", "") + "\n")
    assert ai_desk.LOG_PATH.exists()
    assert "ok" in ai_desk.LOG_PATH.read_text()
