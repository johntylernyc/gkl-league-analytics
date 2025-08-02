import urllib.parse
import config

# === BASE URL ===
base_url = "https://api.login.yahoo.com/oauth2/request_auth"

# === Construct Query Parameters ===
params = {
    "client_id": config.CLIENT_ID,
    "redirect_uri": config.REDIRECT_URI,
    "response_type": "code"
}

query_string = urllib.parse.urlencode(params)
auth_url = f"{base_url}?{query_string}"

print("Visit this URL in your browser to authorize access:")
print(auth_url)