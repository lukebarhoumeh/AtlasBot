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

* OPENAI_MODEL – override model for macro signal (default gpt-4o-mini)
