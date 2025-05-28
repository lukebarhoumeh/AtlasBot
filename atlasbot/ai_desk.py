import asyncio
import json
import logging
import os
from pathlib import Path
import openai

from atlasbot.secrets_loader import get_openai_api_key

openai.api_key = get_openai_api_key()

LOG_PATH = Path(os.getenv("LOG_DIR", "logs")).joinpath("ai_advisor.log")


class AIDesk:
    def __init__(self, ttl: int | None = None):
        if ttl is None:
            ttl = int(os.getenv("GPT_DESK_INTERVAL_MIN", "10")) * 60
        self.ttl = ttl

    async def summarize(self, trades: list[dict]) -> dict:
        if not openai.api_key:
            raise RuntimeError("no_openai_key")
        prompt = (
            "Summarise recent trades and suggest next action. "
            "Return JSON with keys 'summary', 'score', and 'next_action'. "
            f"Trades: {trades}"
        )[:2000]
        resp = await asyncio.to_thread(
            openai.chat.completions.create,
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=60,
            response_format={"type": "json_object"},
        )
        if isinstance(resp, dict):
            return resp
        text = resp.choices[0].message.content.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logging.warning("desk summary JSON decode failed: %s", text)
            return {}


