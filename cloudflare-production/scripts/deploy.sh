#!/bin/bash

# GKL Fantasy Baseball - Cloudflare Deployment Script

echo "=========================================="
echo "GKL Fantasy Baseball - Cloudflare Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check prerequisites
echo ""
echo "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    exit 1
fi
print_status "Node.js installed"

if ! command -v wrangler &> /dev/null; then
    print_warning "Wrangler CLI not installed"
    echo "Installing wrangler..."
    npm install -g wrangler
fi
print_status "Wrangler CLI available"

# Step 1: Database Export
echo ""
echo "Step 1: Exporting database..."
npm run export-db
if [ $? -eq 0 ]; then
    print_status "Database exported successfully"
else
    print_error "Database export failed"
    exit 1
fi

# Step 2: Check wrangler.toml configuration
echo ""
echo "Step 2: Checking configuration..."
if grep -q "TO_BE_ADDED_AFTER_CREATION" wrangler.toml; then
    print_warning "wrangler.toml needs configuration"
    echo "Please run: npm run import-db"
    echo "Then update wrangler.toml with the database_id"
    echo ""
    read -p "Have you completed these steps? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please complete configuration and run this script again"
        exit 1
    fi
fi
print_status "Configuration checked"

# Step 3: Test locally
echo ""
echo "Step 3: Testing locally..."
echo "Starting development server..."
echo "Please test http://localhost:8787/health"
echo "Press Ctrl+C when ready to continue"
npm run dev &
DEV_PID=$!
read -p "Press Enter when ready to continue..."
kill $DEV_PID 2>/dev/null
print_status "Local testing complete"

# Step 4: Deploy to Workers
echo ""
echo "Step 4: Deploying to Cloudflare Workers..."
npm run deploy
if [ $? -eq 0 ]; then
    print_status "Workers deployment successful"
else
    print_error "Workers deployment failed"
    exit 1
fi

# Step 5: Frontend configuration
echo ""
echo "Step 5: Configuring frontend..."
node scripts/update-frontend-api.js
if [ $? -eq 0 ]; then
    print_status "Frontend configured"
else
    print_error "Frontend configuration failed"
    exit 1
fi

# Step 6: Build frontend
echo ""
echo "Step 6: Building frontend..."
cd ../web-ui/frontend
npm run build
if [ $? -eq 0 ]; then
    print_status "Frontend built successfully"
else
    print_error "Frontend build failed"
    exit 1
fi

# Step 7: Deploy to Pages
echo ""
echo "Step 7: Deploying frontend to Cloudflare Pages..."
wrangler pages deploy build/ --project-name gkl-fantasy-frontend
if [ $? -eq 0 ]; then
    print_status "Frontend deployed to Cloudflare Pages"
else
    print_error "Frontend deployment failed"
    exit 1
fi

# Summary
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
print_status "API deployed to Workers"
print_status "Frontend deployed to Pages"
echo ""
echo "Next steps:"
echo "1. Test your Workers API endpoint"
echo "2. Test your Pages frontend URL"
echo "3. Configure custom domain (optional)"
echo "4. Set up monitoring"
echo ""
echo "To view logs: wrangler tail"
echo ""