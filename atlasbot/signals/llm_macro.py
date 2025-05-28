import json
from datetime import datetime, timedelta
import openai

PROMPT = (
    "Summarise the last 12 hours of crypto news. "
    "Return JSON: { 'bias': long|short|neutral, 'confidence': 0-1, "
    "'headline': '...' } max 25 words."
)

class MacroBias:
    def __init__(self, ttl_minutes: int = 60, enabled: bool = True):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.enabled = enabled
        self._cache = (0.0, '', datetime.utcnow() - self.ttl)

    def _call_llm(self) -> tuple[float, str]:
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": PROMPT}],
                temperature=0.3,
                max_tokens=60,
            )
            txt = resp.choices[0].message.content.strip()
            data = json.loads(txt)
            bias = data.get("bias", "neutral").lower()
            conf = float(data.get("confidence", 0))
            score = conf if bias == "long" else -conf if bias == "short" else 0.0
            headline = data.get("headline", "")
            return score, headline
        except Exception as exc:                     # noqa: BLE001
            print(f"[GPT macro error] {exc}")
            return 0.0, ""

    def macro_bias(self, _symbol: str) -> float:
        now = datetime.utcnow()
        score, headline, ts = self._cache
        if not self.enabled:
            return score
        if now - ts >= self.ttl:
            score, headline = self._call_llm()
            self._cache = (score, headline, now)
        return score

_macro = MacroBias()

def macro_bias(symbol: str) -> float:
    return _macro.macro_bias(symbol)
