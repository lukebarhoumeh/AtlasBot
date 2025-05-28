# secrets_loader.py
import boto3
import base64
import json
from botocore.exceptions import ClientError

def load_secret(secret_name: str, region_name: str = "us-east-1") -> dict:
    try:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)
    except Exception:
        return {}

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_data = response.get("SecretString")
        if not secret_data:
            secret_data = base64.b64decode(response["SecretBinary"]).decode("utf-8")
        return json.loads(secret_data)
    except Exception:
        return {}

def get_coinbase_credentials():
    secret = load_secret("atlasbot/coinbase")
    if not secret:
        return {"api_name": "dummy", "private_key": b"dummy"}

    formatted_key = secret["COINBASE_PRIVATE_KEY"].replace("\\n", "\n").strip().encode()

    print("🔐 Loaded Coinbase private key.")
    return {
        "api_name": secret["COINBASE_API_NAME"],
        "private_key": formatted_key,
    }

def get_openai_api_key():
    secret = load_secret("atlasbot/openai")
    return secret.get("OPENAI_API_KEY", "")
