#!/bin/bash
# Script to commit all deployment-related files

echo "==================================="
echo "Committing Deployment Files"
echo "==================================="

# Add GitHub Actions workflow
echo "Adding GitHub Actions workflow..."
git add .github/workflows/data-refresh.yml

# Add CloudFlare Worker files
echo "Adding CloudFlare Worker files..."
git add cloudflare/

# Add incremental update scripts
echo "Adding incremental update scripts..."
git add daily_lineups/incremental_update.py
git add player_stats/incremental_update.py
git add league_transactions/incremental_update.py

# Add change tracking system
echo "Adding change tracking system..."
git add scripts/change_tracking.py
git add database/schema/
git add database/migrations/
git add database/create_transactions_table.py
git add database/apply_change_tracking_schema.py

# Add token manager
echo "Adding token manager..."
git add auth/token_manager.py

# Add deployment documentation
echo "Adding deployment documentation..."
git add deployment/
git add docs/prds/prd-scheduled-data-refreshes-prod-and-local.md

# Show what will be committed
echo ""
echo "Files to be committed:"
git status --short | grep "^A"

echo ""
echo "Ready to commit. Run the following commands:"
echo ""
echo "git commit -m \"Add automated data refresh system with CloudFlare Worker and GitHub Actions\""
echo "git push origin main"
echo ""
echo "After pushing, go to GitHub and check the Actions tab!"