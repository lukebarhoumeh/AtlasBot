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
