# AtlasBot

Mini research and trading framework for Coinbase markets.

```
+-----------+   +------------+   +---------------+
| market    |-->|  signals   |-->| decision      |
|  data     |   | (3 feeds)  |   |  engine       |
+-----------+   +------------+   +---------------+
       ^                |                |
       |                v                v
       |            +-------+        +---------+
       |            | risk  |<------>| trader  |
       |            +-------+        +---------+
       |                                |
       +--------------------------------+
                                    execution
```

## Usage

Run the bot in simulation or paper mode:

```bash
python -m cli.run_bot --backend sim   # default
python -m cli.run_bot --backend paper
```

Metrics are exposed at http://localhost:9000/metrics. GPT desk summaries are
written to `logs/ai_advisor.log` every 10 minutes when `OPENAI_API_KEY` is set.

## Environment vars

* OPENAI_API_KEY      – optional, enable GPT desk
* COINBASE_PAPER_KEY  – optional, send orders to Coinbase paper
* LOG_LEVEL           – DEBUG|INFO|WARN|ERROR (default INFO)
* OPENAI_MODEL        – override model for macro signal (default gpt-4o-mini)

## Troubleshooting

**`no_openai_key` error** – The bot tried to call GPT features but no API key
was found. Set the `OPENAI_API_KEY` environment variable to your OpenAI key, or
store it in the AWS secret `atlasbot/openai` so `secrets_loader` can retrieve
it.
