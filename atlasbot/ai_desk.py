import json
import asyncio
import os
import openai

from atlasbot.secrets_loader import get_openai_api_key

openai.api_key = get_openai_api_key()


class AIDesk:
    def __init__(self, ttl: int = 600):
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
        return json.loads(text)


