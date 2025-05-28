import openai
from atlasbot.secrets_loader import get_openai_api_key

openai.api_key = get_openai_api_key()
from datetime import datetime, timedelta, timezone

class GPTTrendAnalyzer:
    """
    Caches GPT sentiment per symbol; refreshes every `ttl_minutes`.
    """
    def __init__(self, enabled: bool = True, ttl_minutes: int = 30):
        self.enabled = enabled
        self.ttl = timedelta(minutes=ttl_minutes)
        self._cache = {}  # symbol -> (sentiment, timestamp)

    # --------------------------------------------------------------------- #
    def get_trend_confidence(self, symbol: str) -> str:
        if not self.enabled:
            return "NEUTRAL"

        cached = self._cache.get(symbol)
        if cached and datetime.now(timezone.utc) - cached[1] < self.ttl:
            return cached[0]

        sentiment = self._call_gpt(symbol)
        self._cache[symbol] = (sentiment, datetime.now(timezone.utc))
        return sentiment

    # --------------------------------------------------------------------- #
    @staticmethod
    def _call_gpt(symbol: str) -> str:
        prompt = (
            f"Classify the near-term outlook (next few hours) for {symbol} as "
            "BULL, NEUTRAL, or BEAR based only on its recent price action "
            "and general market sentiment. Reply with one word."
        )
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",     # cheaper model for high-freq calls
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1,
            )
            raw = resp.choices[0].message.content.strip().upper()
            return raw if raw in {"BULL", "NEUTRAL", "BEAR"} else "NEUTRAL"
        except Exception as exc:
            print(f"[GPT ERROR] {symbol}: {exc}")
            return "NEUTRAL"
