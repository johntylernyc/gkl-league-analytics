# Setting Up Yahoo API Authentication

## Prerequisites

1. **Yahoo Developer Account**: Create one at https://developer.yahoo.com
2. **Register Your App**: 
   - Go to https://developer.yahoo.com/apps/
   - Create a new app
   - Set redirect URI to: `https://localhost:8000`
   - Note your Client ID and Client Secret

## Setup Steps

### 1. Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:YAHOO_CLIENT_ID = "your_client_id_here"
$env:YAHOO_CLIENT_SECRET = "your_client_secret_here"
```

**Windows (Command Prompt):**
```cmd
set YAHOO_CLIENT_ID=your_client_id_here
set YAHOO_CLIENT_SECRET=your_client_secret_here
```

**Or create a .env file in the project root:**
```
YAHOO_CLIENT_ID=your_client_id_here
YAHOO_CLIENT_SECRET=your_client_secret_here
```

### 2. Generate Authorization URL

```bash
python auth/generate_auth_url.py
```

This will output a URL. Open it in your browser and authorize the app.

### 3. Get Authorization Code

After authorizing, you'll be redirected to a URL like:
```
https://localhost:8000/?code=AUTHORIZATION_CODE_HERE
```

Copy the authorization code.

### 4. Set Authorization Code

**PowerShell:**
```powershell
$env:YAHOO_AUTHORIZATION_CODE = "your_authorization_code_here"
```

**Command Prompt:**
```cmd
set YAHOO_AUTHORIZATION_CODE=your_authorization_code_here
```

### 5. Initialize Tokens

```bash
python auth/initialize_tokens.py
```

This will create a `tokens.json` file with your access and refresh tokens.

### 6. Test Authentication

```bash
python auth/test_auth.py
```

You should see "Authentication successful!"

## Troubleshooting

### Invalid Consumer Key Error
- Verify your Client ID is correct
- Check that environment variables are set
- Try restarting your terminal/PowerShell

### Token Expiration
Yahoo tokens expire after 1 hour. The system will automatically refresh them, but if you get authentication errors:
```bash
python auth/initialize_tokens.py
```

### Using Existing Credentials
If you have working credentials from another session, you can:
1. Copy the working `tokens.json` file to this directory
2. Set the same environment variables