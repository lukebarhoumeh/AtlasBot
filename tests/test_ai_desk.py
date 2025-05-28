import asyncio
import openai
from atlasbot.ai_desk import AIDesk


def test_ai_summary(monkeypatch):
    monkeypatch.setattr(openai.chat.completions, "create", lambda *a, **k: {"summary": "ok", "score": 0.2, "next_action": "flat"})
    monkeypatch.setattr(openai, "api_key", "x")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    out = asyncio.run(AIDesk().summarize([]))
    assert out["summary"] == "ok"
    assert out["next_action"] == "flat"



