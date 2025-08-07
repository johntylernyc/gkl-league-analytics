# Notion Integration Setup Guide

## Steps to Connect Your Notion Integration

1. **Go to Notion Integrations Page**
   - Visit: https://www.notion.so/my-integrations
   - You should see your integration (or create a new one)

2. **Configure Your Integration**
   - Name: "GKL League Analytics Sync"
   - Associated workspace: Select your workspace
   - Capabilities needed:
     - ✅ Read content
     - ✅ Read comments (optional)
     - ❌ Write/Update (not needed for sync)

3. **Share Your PRD Page with the Integration**
   - Open your GKL-LEAGUE-ANALYTICS page in Notion
   - Click the "..." menu in the top right
   - Select "Add connections" or "Connect to"
   - Search for and select your integration name
   - Click "Confirm"

4. **Verify the Connection**
   - The integration should now appear under "Connections" on the page
   - All child pages and databases will inherit this permission

5. **Run the Sync Script**
   ```bash
   python scripts/sync_notion_prds.py
   ```

## Alternative: Using Internal Integration Token

If you're using an internal integration token (starts with `ntn_`), make sure:
1. The integration is created in the same workspace as your PRDs
2. The integration has been explicitly shared with the page
3. The page ID is correct (extracted from the URL)

## Troubleshooting

- **404 Error**: The page hasn't been shared with the integration
- **401 Error**: Invalid token or expired credentials
- **403 Error**: Integration lacks required permissions

Once connected, the sync script will:
- Pull all PRDs from your Notion workspace
- Convert them to markdown format
- Store them in `docs/prds/` directory
- Allow Claude Code to reference them for implementation planning