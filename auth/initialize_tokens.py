import requests
import base64
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# === CONFIGURATION ===
CLIENT_ID = os.getenv('YAHOO_CLIENT_ID')
CLIENT_SECRET = os.getenv('YAHOO_CLIENT_SECRET')
REDIRECT_URI = os.getenv('YAHOO_REDIRECT_URI', 'https://goldenknightlounge.com')
AUTH_CODE = os.getenv('YAHOO_AUTHORIZATION_CODE')
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

# === Prepare Auth Header ===
credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
headers = {
    "Authorization": f"Basic {encoded_credentials}",
    "Content-Type": "application/x-www-form-urlencoded"
}

# === Token Request Payload ===
data = {
    "grant_type": "authorization_code",
    "code": AUTH_CODE,
    "redirect_uri": REDIRECT_URI
}

# === Request Tokens ===
response = requests.post(TOKEN_URL, headers=headers, data=data)
response.raise_for_status()
tokens = response.json()

# === Save Tokens to File in Current Directory ===
current_dir = os.path.dirname(os.path.abspath(__file__))
tokens_path = os.path.join(current_dir, "tokens.json")
with open(tokens_path, "w") as f:
    json.dump(tokens, f, indent=4)

print(f"tokens.json created at {tokens_path}. You can now run your Yahoo Fantasy scripts.")
