import json
import logging
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from atlasbot.config import OPENAI_MODEL

import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

PROMPT = (
    "Summarise the last 12 hours of crypto news. "
    "Return JSON: { 'bias': long|short|neutral, 'confidence': 0-1, "
    "'headline': '...' } max 25 words."
)

class MacroBias:
    def __init__(self, ttl_minutes: int = 60, enabled: bool = True):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.enabled = enabled
        self._cache = (0.0, 'llm_offline', datetime.now(timezone.utc) - self.ttl)
        self._last_warn = datetime.now(timezone.utc) - timedelta(hours=1)

    def _warn(self, reason: str) -> None:
        now = datetime.now(timezone.utc)
        if now - self._last_warn >= timedelta(hours=1):
            logging.warning("llm_macro disabled: %s", reason)
            self._last_warn = now

    def _call_llm(self) -> tuple[float, str]:
        if not client.api_key:
            self._warn("no api key")
            return 0.0, "llm_offline"
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": PROMPT}],
                temperature=0.3,
                max_tokens=60,
                response_format={"type": "json_object"},
            )
            txt = resp.choices[0].message.content.strip()
            data = json.loads(txt)
            bias = data.get("bias", "neutral").lower()
            conf = float(data.get("confidence", 0))
            score = conf if bias == "long" else -conf if bias == "short" else 0.0
            headline = data.get("headline", "")
            return score, headline
        except Exception as exc:                     # noqa: BLE001
            self._warn(str(exc))
            return 0.0, "llm_offline"

    def macro_bias(self, _symbol: str) -> float:
        now = datetime.now(timezone.utc)
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
