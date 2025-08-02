import requests
import json
import base64
import xml.etree.ElementTree as ET
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, TOKEN_URL, BASE_FANTASY_URL, AUTHORIZATION_CODE

# ---- CONFIGURATION ----
GAME_KEY = 'mlb'

# ---- FUNCTIONS ----
def exchange_code_for_tokens():
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": AUTHORIZATION_CODE
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    tokens = response.json()
    with open('tokens.json', 'w') as f:
        json.dump(tokens, f, indent=4)
    return tokens['access_token'], tokens['refresh_token']

def get_access_token(refresh_token):
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'refresh_token',
        'redirect_uri': REDIRECT_URI,
        'refresh_token': refresh_token
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    return response.json()['access_token']

def fetch_stat_categories(access_token):
    url = f"{BASE_FANTASY_URL}/game/{GAME_KEY}/stat_categories?format=json"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def parse_stat_categories(json_data):
    stat_mappings = {}
    stats = json_data['fantasy_content']['game'][1]['stat_categories']['stats']

    for stat_obj in stats:
        if isinstance(stat_obj, dict) and 'stat' in stat_obj:
            stat = stat_obj['stat']
            stat_id = int(stat['stat_id'])
            stat_name = stat['name']
            stat_mappings[stat_id] = stat_name
        # skip if it’s just the "count" value

    return stat_mappings

def save_stat_mappings(stat_mappings):
    import os
    metadata_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'metadata'))
    stat_mappings_path = os.path.join(metadata_dir, 'stat_mappings.json')
    with open(stat_mappings_path, 'w') as f:
        json.dump(stat_mappings, f, indent=4)
    print(f"Saved stat_mappings.json to {stat_mappings_path}")

# ---- MAIN ----
if __name__ == '__main__':
    try:
        try:
            with open('tokens.json', 'r') as f:
                tokens = json.load(f)
                refresh_token = tokens['refresh_token']
            print("Refreshing access token...")
            access_token = get_access_token(refresh_token)
        except (FileNotFoundError, KeyError):
            print("No refresh token found. Exchanging authorization code...")
            access_token, refresh_token = exchange_code_for_tokens()

        print("Fetching stat categories...")
        json_data = fetch_stat_categories(access_token)

        print("Parsing stat categories...")
        stat_mappings = parse_stat_categories(json_data)

        print(f"Found {len(stat_mappings)} stats. Saving to JSON...")
        save_stat_mappings(stat_mappings)

        print("Done! Stat ID → Stat Name mapping exported.")

    except Exception as e:
        print(f"An error occurred: {e}")