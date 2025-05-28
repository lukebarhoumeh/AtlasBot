import asyncio
import json
import logging
import os
from pathlib import Path
import openai
import time
from openai import OpenAI

from atlasbot.secrets_loader import get_openai_api_key
from atlasbot import metrics

client = OpenAI(api_key=get_openai_api_key())

LOG_PATH = Path(os.getenv("AI_ADVISOR_LOG", "logs/ai_advisor.log"))


def _safe_chat(prompt: str, *, model: str, retries=(0, 2, 5, 15, 60)) -> dict:
    no_key_warned = getattr(_safe_chat, "_warned", False)
    if not client.api_key:
        if not no_key_warned:
            logging.warning("GPT desk disabled: no API key")
            _safe_chat._warned = True
        return {"bias": "neutral", "confidence": 0, "headline": "fallback"}
    for delay in retries:
        if delay:
            time.sleep(delay)
        try:
            rsp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=30,
            )
            metrics.gpt_last_success_ts.set(time.time())
            return json.loads(rsp.choices[0].message.content)
        except (json.JSONDecodeError, openai.RateLimitError, openai.APIError) as exc:
            logging.warning("GPT desk retry in %ss (%s)", delay, exc)
    metrics.gpt_errors_total.inc()
    return {"bias": "neutral", "confidence": 0, "headline": "fallback"}


class AIDesk:
    def __init__(self, ttl: int | None = None):
        if ttl is None:
            ttl = int(os.getenv("GPT_DESK_INTERVAL_MIN", "10")) * 60
        self.ttl = ttl

    async def summarize(self, trades: list[dict]) -> dict:
        prompt = (
            "Summarise recent trades and suggest next action. "
            "Return JSON with keys 'summary', 'score', and 'next_action'. "
            f"Trades: {trades}"
        )[:2000]
        return await asyncio.to_thread(
            _safe_chat,
            prompt,
            model="gpt-4o",
        )


