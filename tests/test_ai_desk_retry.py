from types import SimpleNamespace
import atlasbot.ai_desk as desk


def test_ai_retry(monkeypatch):
    responses = ["{", "{", '{"bias":"long","confidence":0.5,"headline":"ok"}']

    def fake_create(*a, **k):
        txt = responses.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=txt))])

    monkeypatch.setattr(desk.client.chat.completions, "create", fake_create)
    desk.client.api_key = "x"
    desk.metrics.gpt_errors_total._value.set(0)
    first = desk._safe_chat("hi", model="gpt", retries=(0, 0))
    assert first["bias"] == "neutral"
    second = desk._safe_chat("hi", model="gpt", retries=(0,))
    assert second["bias"] == "long"
    assert desk.metrics.gpt_errors_total._value.get() >= 1
