"""AtlasBot – automated crypto trading package."""

from dotenv import load_dotenv

load_dotenv()
__all__ = [
    "config",
    "market_data",
    "utils",
    "trader",
    "gpt_report",
    "secrets_loader",
    "signals",
    "decision_engine",
    "risk",
    "execution",
]
__version__ = "0.3.0"
