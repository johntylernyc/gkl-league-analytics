# Authentication Documentation

This document provides technical documentation for the Yahoo Fantasy Sports OAuth2 authentication system.

## Authentication System Overview

The authentication system implements OAuth2 authorization flow for secure access to Yahoo Fantasy Sports API. It consists of four Python scripts that handle the complete authentication lifecycle from initial authorization to token refresh.

### File Structure
```
auth/
├── config.py              # Configuration and credentials
├── generate_auth_url.py    # OAuth2 authorization URL generation
├── initialize_tokens.py    # Authorization code to token exchange
├── test_auth.py           # Authentication validation and testing
└── tokens.json            # Token storage (generated)
```

## Component Documentation

### config.py
**Purpose**: Central configuration management for authentication credentials and API endpoints.

**Configuration Variables**:
- `CLIENT_ID`: Yahoo application client identifier
- `CLIENT_SECRET`: Yahoo application client secret
- `REDIRECT_URI`: OAuth2 redirect URI for authorization callback
- `AUTHORIZATION_CODE`: Temporary authorization code from Yahoo OAuth flow
- `TOKEN_URL`: Yahoo OAuth2 token endpoint
- `BASE_FANTASY_URL`: Yahoo Fantasy Sports API base URL
- `LEAGUE_KEY`: Target fantasy league identifier

### generate_auth_url.py
**Purpose**: Generates Yahoo OAuth2 authorization URL for user consent.

**Functionality**:
- Constructs OAuth2 authorization URL with required parameters
- Uses `authorization_code` grant type
- Outputs URL for manual browser authorization

**Usage**:
```bash
python generate_auth_url.py
```

### initialize_tokens.py
**Purpose**: Exchanges authorization code for access and refresh tokens.

**Process**:
1. Reads authorization code from `config.py`
2. Encodes client credentials using Base64
3. Exchanges authorization code for tokens via POST request
4. Saves tokens to `tokens.json` in current directory

**Token Exchange Flow**:
- Grant type: `authorization_code`
- Authentication: Basic auth with Base64 encoded client credentials
- Output: Access token and refresh token saved to JSON file

### test_auth.py
**Purpose**: Validates authentication and tests API connectivity.

**Key Functions**:
- `exchange_code_for_tokens()`: Alternative token exchange method
- `get_access_token(refresh_token)`: Refresh expired access tokens
- `fetch_stat_categories(access_token)`: Test API call to validate authentication
- `parse_stat_categories()`: Parse Yahoo stat metadata
- `save_stat_mappings()`: Save stat mappings to metadata directory

**Authentication Flow**:
1. Attempts to load existing refresh token from `tokens.json`
2. If available, refreshes access token
3. If not available, exchanges authorization code for new tokens
4. Tests authentication with API call to fetch stat categories

### tokens.json
**Purpose**: Stores OAuth2 tokens for API authentication.

**Structure**:
```json
{
    "access_token": "Bearer token for API requests",
    "refresh_token": "Token for refreshing expired access tokens",
    "expires_in": 3600,
    "token_type": "bearer"
}
```

## OAuth2 Implementation Details

### Authorization Flow
1. **Authorization Request**: User visits generated URL to grant access
2. **Authorization Code**: Yahoo redirects with temporary authorization code
3. **Token Exchange**: Code is exchanged for access and refresh tokens
4. **API Access**: Access token used for authenticated API requests
5. **Token Refresh**: Refresh token used to obtain new access tokens when expired

### Token Lifecycle
- **Access Token**: Valid for 1 hour (3600 seconds)
- **Refresh Token**: Long-lived token for obtaining new access tokens
- **Automatic Refresh**: Implemented in data collection scripts
- **Manual Refresh**: Available via `test_auth.py`

### Authentication Headers
**Token Exchange**:
```
Authorization: Basic <base64(client_id:client_secret)>
Content-Type: application/x-www-form-urlencoded
```

**API Requests**:
```
Authorization: Bearer <access_token>
```

## Setup & Usage Guide

### Initial Setup
1. **Generate Authorization URL**:
   ```bash
   cd auth
   python generate_auth_url.py
   ```

2. **Authorize Application**:
   - Visit the generated URL in browser
   - Login to Yahoo and authorize application
   - Copy authorization code from redirect URL

3. **Update Configuration**:
   - Edit `config.py`
   - Replace `AUTHORIZATION_CODE` with copied code

4. **Initialize Tokens**:
   ```bash
   python initialize_tokens.py
   ```

### Token Refresh
**Manual Refresh**:
```bash
python test_auth.py
```

**Automatic Refresh**:
- Handled automatically by data collection scripts
- Occurs when access token expires (every hour)

### Authentication Testing
```bash
python test_auth.py
```
- Tests token validity
- Fetches stat categories to verify API access
- Saves stat mappings to metadata directory

## Technical Reference

### Yahoo OAuth2 Endpoints
- **Authorization**: `https://api.login.yahoo.com/oauth2/request_auth`
- **Token**: `https://api.login.yahoo.com/oauth2/get_token`
- **API Base**: `https://fantasysports.yahooapis.com/fantasy/v2`

### Token Request Parameters
**Authorization Code Exchange**:
```
grant_type: authorization_code
code: <authorization_code>
redirect_uri: <redirect_uri>
```

**Refresh Token**:
```
grant_type: refresh_token
refresh_token: <refresh_token>
redirect_uri: <redirect_uri>
```

### Error Handling
- **400 Bad Request**: Invalid or expired authorization code
- **401 Unauthorized**: Invalid client credentials
- **Token Expiration**: Automatic refresh via refresh token
- **Network Errors**: Retry logic implemented in collection scripts

### Security Considerations
- Client credentials stored in plaintext configuration file
- Tokens stored in JSON file on local filesystem
- Access tokens expire every hour for security
- Refresh tokens provide long-term access without re-authorization