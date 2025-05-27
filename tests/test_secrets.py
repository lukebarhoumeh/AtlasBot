# tests/test_secrets.py
from atlasbot.secrets_loader import get_coinbase_credentials

def test_secret_loader():
    assert get_coinbase_credentials() is not None
