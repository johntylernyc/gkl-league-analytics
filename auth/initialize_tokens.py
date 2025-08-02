import requests
import base64
import json
import os
import config

# === CONFIGURATION ===
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
REDIRECT_URI = config.REDIRECT_URI
AUTH_CODE = config.AUTHORIZATION_CODE  # Use authorization code from config.py
TOKEN_URL = config.TOKEN_URL

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
