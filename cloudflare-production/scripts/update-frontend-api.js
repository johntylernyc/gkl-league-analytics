#!/usr/bin/env node

/**
 * Update frontend API configuration for Cloudflare Workers
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(prompt) {
  return new Promise(resolve => {
    rl.question(prompt, resolve);
  });
}

async function main() {
  console.log('=== Frontend API Configuration Update ===\n');
  
  const workerUrl = await question('Enter your Worker URL (e.g., https://gkl-fantasy-api.your-subdomain.workers.dev): ');
  
  if (!workerUrl) {
    console.log('Worker URL is required');
    process.exit(1);
  }
  
  // Create updated API service file
  const apiServicePath = path.join(__dirname, '../../web-ui/frontend/src/services/api.js');
  
  const apiServiceContent = `/**
 * API Service - Configured for Cloudflare Workers
 */

const API_URL = process.env.REACT_APP_API_URL || '${workerUrl}';

class ApiService {
  async request(endpoint, options = {}) {
    const url = \`\${API_URL}\${endpoint}\`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        throw new Error(\`API error: \${response.status}\`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Transactions
  async getTransactions(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(\`/api/transactions?\${queryString}\`);
  }

  async getTransaction(id) {
    return this.request(\`/api/transactions/\${id}\`);
  }

  // Analytics
  async getAnalyticsOverview(season) {
    return this.request(\`/api/analytics/overview?season=\${season}\`);
  }

  async getAnalyticsTrends(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(\`/api/analytics/trends?\${queryString}\`);
  }

  // Players
  async getPlayers(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(\`/api/players?\${queryString}\`);
  }

  async getPlayer(playerId) {
    return this.request(\`/api/players/\${playerId}\`);
  }

  async getPlayerStats(playerId, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(\`/api/players/\${playerId}/stats?\${queryString}\`);
  }

  // Player Spotlight
  async getPlayerSpotlight(playerId, season) {
    return this.request(\`/api/player-spotlight/\${playerId}?season=\${season}\`);
  }

  async getPlayerTimeline(playerId, season) {
    return this.request(\`/api/player-spotlight/\${playerId}/timeline?season=\${season}\`);
  }

  // Lineups
  async getLineups(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(\`/api/lineups?\${queryString}\`);
  }

  async getDailyLineups(date) {
    return this.request(\`/api/lineups/\${date}\`);
  }

  async getTeamLineup(date, teamId) {
    return this.request(\`/api/lineups/\${date}/team/\${teamId}\`);
  }

  // Health check
  async checkHealth() {
    return this.request('/health');
  }
}

export default new ApiService();
`;

  // Write the updated API service
  fs.writeFileSync(apiServicePath, apiServiceContent);
  console.log(`\n✅ Updated: ${apiServicePath}`);
  
  // Create .env.production file
  const envPath = path.join(__dirname, '../../web-ui/frontend/.env.production');
  const envContent = `REACT_APP_API_URL=${workerUrl}\n`;
  
  fs.writeFileSync(envPath, envContent);
  console.log(`✅ Created: ${envPath}`);
  
  console.log('\n📦 Next steps:');
  console.log('1. cd ../web-ui/frontend');
  console.log('2. npm run build');
  console.log('3. Deploy build/ folder to Cloudflare Pages');
  
  rl.close();
}

main();