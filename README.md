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

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

Tests expect the package to be installed in editable mode.

## Usage

Run the bot in simulation or paper mode:

```bash
python -m cli.run_bot --backend sim   # default
python -m cli.run_bot --backend paper
```

Fees are refreshed hourly by a background updater started at launch.
Strong signals have their profit target scaled so the expected edge exceeds
fees and slippage.

Metrics are exposed at http://localhost:9000/metrics. GPT desk summaries are
written to `logs/ai_advisor.log` every 10 minutes when `OPENAI_API_KEY` is set.
Metrics include `atlasbot_feed_watchdog_total` alongside PnL and latency gauges.
New gauges track edge quality, trade cadence and exit types.

## Environment vars

* OPENAI_API_KEY      – optional, enable GPT desk
* COINBASE_PAPER_KEY  – optional, send orders to Coinbase paper
* LOG_LEVEL           – DEBUG|INFO|WARN|ERROR (default INFO)
* OPENAI_MODEL        – override model for macro signal (default gpt-4o-mini)
* EXECUTION_MODE      – maker | taker (default maker)
* MIN_EDGE_BPS        – minimum edge threshold
* CYCLE_SEC          – main loop delay seconds (default 1)
* SYMBOLS            – comma list of trading pairs
* MAX_NOTIONAL       – position size USD cap (default 200)
* PAPER_CASH         – starting cash for paper or sim
* CONFLICT_THRESH     – orderflow/momentum disagreement cutoff
* MACRO_TTL_MIN       – minutes to cache GPT macro bias
* BREAKOUT_WEIGHT     – ensemble weight for breakout signal
* K_TP                – ATR-based take profit multiplier
* K_SL                – ATR-based stop loss multiplier
* MAX_HOLD_MIN        – maximum hold time in minutes
* ALLOW_CONFLICT      – allow conflict trades if true

## Troubleshooting

**`no_openai_key` error** – The bot tried to call GPT features but no API key
was found. Set the `OPENAI_API_KEY` environment variable to your OpenAI key, or
store it in the AWS secret `atlasbot/openai` so `secrets_loader` can retrieve
it.

**Refreshing market data** – To reset the MarketData singleton during tests or
runtime, set `atlasbot.market_data._market = None` and call `get_market()`
again. The helper will now create a fresh instance automatically.
