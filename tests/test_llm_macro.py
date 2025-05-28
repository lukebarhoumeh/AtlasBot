import atlasbot.signals.llm_macro as lm

class Resp:
    def __init__(self):
        self.choices = [type("X", (object,), {
            "message": type("Y", (object,), {
                "content": '{"bias":"long","confidence":0.6,"headline":"test"}'
            })()
        })]

def test_macro_bias(monkeypatch):
    monkeypatch.setattr(lm.client.chat.completions, "create", lambda *a, **k: Resp())
    monkeypatch.setattr(lm.client, "api_key", "x")
    monkeypatch.setattr(lm, "_macro", lm.MacroBias())
    assert lm.macro_bias("BTC-USD") == 0.6

def test_safe_mode(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(lm.client, "api_key", "")
    monkeypatch.setattr(lm, "_macro", lm.MacroBias())
    assert lm.macro_bias("BTC-USD") == 0.0
