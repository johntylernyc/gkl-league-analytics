"""
Token manager for Yahoo OAuth.
Handles token refresh and storage for both local and GitHub Actions environments.
"""

import os
import json
import base64
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

class YahooTokenManager:
    """Manages Yahoo OAuth tokens with automatic refresh."""
    
    def __init__(self):
        """Initialize token manager."""
        self.client_id = os.getenv('YAHOO_CLIENT_ID')
        self.client_secret = os.getenv('YAHOO_CLIENT_SECRET')
        self.redirect_uri = os.getenv('YAHOO_REDIRECT_URI')
        self.token_url = 'https://api.login.yahoo.com/oauth2/get_token'
        
        # Token storage
        self.token_file = Path(__file__).parent / 'tokens.json'
        self.tokens = self._load_tokens()
        
    def _load_tokens(self) -> Dict:
        """Load tokens from file or environment."""
        # First try to load from file (local development)
        if self.token_file.exists():
            with open(self.token_file, 'r') as f:
                tokens = json.load(f)
                # Add expiry time if not present
                if 'expires_at' not in tokens:
                    tokens['expires_at'] = (datetime.now() + timedelta(seconds=3600)).isoformat()
                return tokens
        
        # In GitHub Actions, use refresh token from environment
        refresh_token = os.getenv('YAHOO_REFRESH_TOKEN')
        if refresh_token:
            print(f"Using refresh token from environment variable (GitHub Actions)")
            return {
                'refresh_token': refresh_token,
                'access_token': None,
                'expires_at': datetime.now().isoformat()  # Force refresh
            }
        
        # Try legacy AUTHORIZATION_CODE (one-time use)
        auth_code = os.getenv('YAHOO_AUTHORIZATION_CODE')
        if auth_code and len(auth_code) < 50:  # Auth codes are shorter than refresh tokens
            # This is likely a one-time auth code, exchange it for tokens
            return self._exchange_auth_code(auth_code)
        elif auth_code:
            # This might actually be a refresh token mislabeled
            return {
                'refresh_token': auth_code,
                'access_token': None,
                'expires_at': datetime.now().isoformat()  # Force refresh
            }
        
        raise ValueError("No valid tokens found. Please run auth flow first.")
    
    def _exchange_auth_code(self, auth_code: str) -> Dict:
        """Exchange authorization code for tokens."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(self.token_url, headers=headers, data=data)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to exchange auth code: {response.text}")
        
        tokens = response.json()
        tokens['expires_at'] = (datetime.now() + timedelta(seconds=tokens['expires_in'])).isoformat()
        
        # Save tokens for future use
        self._save_tokens(tokens)
        
        return tokens
    
    def _refresh_access_token(self) -> str:
        """Refresh the access token using refresh token."""
        if not self.tokens.get('refresh_token'):
            raise ValueError("No refresh token available")
        
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.tokens['refresh_token'],
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(self.token_url, headers=headers, data=data)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to refresh token: {response.text}")
        
        new_tokens = response.json()
        
        # Update stored tokens
        self.tokens['access_token'] = new_tokens['access_token']
        self.tokens['expires_at'] = (datetime.now() + timedelta(seconds=new_tokens['expires_in'])).isoformat()
        
        # Keep the refresh token (Yahoo reuses it)
        if 'refresh_token' in new_tokens:
            self.tokens['refresh_token'] = new_tokens['refresh_token']
        
        # Save updated tokens
        self._save_tokens(self.tokens)
        
        return self.tokens['access_token']
    
    def _save_tokens(self, tokens: Dict):
        """Save tokens to file."""
        # Only save to file if we're in local development
        if not os.getenv('GITHUB_ACTIONS'):
            with open(self.token_file, 'w') as f:
                json.dump(tokens, f, indent=4)
    
    def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        # Check if we have a valid access token
        if self.tokens.get('access_token') and self.tokens.get('expires_at'):
            expires_at = datetime.fromisoformat(self.tokens['expires_at'])
            if datetime.now() < expires_at - timedelta(minutes=5):  # 5 min buffer
                return self.tokens['access_token']
        
        # Need to refresh
        return self._refresh_access_token()
    
    def test_token(self) -> bool:
        """Test if the current token works."""
        try:
            access_token = self.get_access_token()
            
            # Test with a simple API call
            url = "https://fantasysports.yahooapis.com/fantasy/v2/game/mlb"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Token test failed: {e}")
            return False


def get_yahoo_headers() -> Dict[str, str]:
    """Get headers with valid Yahoo access token."""
    manager = YahooTokenManager()
    access_token = manager.get_access_token()
    
    return {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }


if __name__ == "__main__":
    # Test the token manager
    print("Testing Yahoo Token Manager...")
    
    try:
        manager = YahooTokenManager()
        
        # Test getting access token
        access_token = manager.get_access_token()
        print(f"Access token obtained: {access_token[:20]}...")
        
        # Test the token
        if manager.test_token():
            print("[OK] Token is valid and working!")
        else:
            print("[FAIL] Token test failed")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        print("\nMake sure you have either:")
        print("1. A valid tokens.json file in the auth/ directory")
        print("2. YAHOO_REFRESH_TOKEN environment variable set")
        print("3. Run the OAuth flow: python auth/generate_auth_url.py")