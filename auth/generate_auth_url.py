import urllib.parse
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# === BASE URL ===
base_url = "https://api.login.yahoo.com/oauth2/request_auth"

# === Construct Query Parameters ===
params = {
    "client_id": os.getenv('YAHOO_CLIENT_ID'),
    "redirect_uri": os.getenv('YAHOO_REDIRECT_URI', 'https://goldenknightlounge.com'),
    "response_type": "code"
}

query_string = urllib.parse.urlencode(params)
auth_url = f"{base_url}?{query_string}"

print("Visit this URL in your browser to authorize access:")
print(auth_url)