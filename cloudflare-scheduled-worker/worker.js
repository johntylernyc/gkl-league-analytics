/**
 * CloudFlare Worker for GKL Fantasy Baseball Analytics
 * Handles scheduled data refreshes at 6AM, 1PM, and 10PM ET
 * Triggers GitHub Actions workflows for data collection
 */

// Configuration
const GITHUB_OWNER = 'your-github-username';  // Update with your GitHub username
const GITHUB_REPO = 'gkl-league-analytics';
const GITHUB_WORKFLOW_FILE = 'data-refresh.yml';
const TIMEZONE = 'America/New_York';

// Environment variables (set in CloudFlare dashboard)
// GITHUB_TOKEN - GitHub Personal Access Token with workflow permissions
// SLACK_WEBHOOK_URL - Optional: Slack webhook for notifications
// DISCORD_WEBHOOK_URL - Optional: Discord webhook for notifications

/**
 * Main handler for scheduled events
 */
addEventListener('scheduled', event => {
  event.waitUntil(handleSchedule(event));
});

/**
 * Main handler for HTTP requests (for manual triggers and monitoring)
 */
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

/**
 * Handle scheduled executions
 */
async function handleSchedule(event) {
  const now = new Date();
  const etTime = new Intl.DateTimeFormat('en-US', {
    timeZone: TIMEZONE,
    hour: 'numeric',
    hour12: false
  }).format(now);
  
  const hour = parseInt(etTime);
  
  // Determine refresh type based on time
  let refreshType;
  if (hour === 6) {
    refreshType = 'morning';
  } else if (hour === 13) {
    refreshType = 'afternoon';
  } else if (hour === 22) {
    refreshType = 'night';
  } else {
    console.log(`Scheduled run at unexpected hour: ${hour}`);
    refreshType = 'adhoc';
  }
  
  console.log(`Starting ${refreshType} refresh at ${now.toISOString()}`);
  
  try {
    // Trigger GitHub Actions workflow
    const result = await triggerGitHubWorkflow(refreshType);
    
    // Send notifications
    await sendNotifications({
      type: 'refresh_started',
      refreshType,
      timestamp: now.toISOString(),
      workflowRun: result.run_id
    });
    
    return new Response('Workflow triggered successfully', { status: 200 });
  } catch (error) {
    console.error('Error triggering workflow:', error);
    
    // Send error notifications
    await sendNotifications({
      type: 'refresh_failed',
      refreshType,
      timestamp: now.toISOString(),
      error: error.message
    });
    
    throw error;
  }
}

/**
 * Handle HTTP requests for manual triggers and status checks
 */
async function handleRequest(request) {
  const url = new URL(request.url);
  
  // Health check endpoint
  if (url.pathname === '/health') {
    return new Response(JSON.stringify({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      timezone: TIMEZONE
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  // Manual trigger endpoint
  if (url.pathname === '/trigger' && request.method === 'POST') {
    // Verify authorization
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response('Unauthorized', { status: 401 });
    }
    
    try {
      const body = await request.json();
      const refreshType = body.refreshType || 'manual';
      
      const result = await triggerGitHubWorkflow(refreshType);
      
      return new Response(JSON.stringify({
        success: true,
        refreshType,
        workflowRun: result.run_id,
        timestamp: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      return new Response(JSON.stringify({
        success: false,
        error: error.message
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
  
  // Status endpoint
  if (url.pathname === '/status') {
    const status = await getWorkflowStatus();
    return new Response(JSON.stringify(status), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  return new Response('Not Found', { status: 404 });
}

/**
 * Trigger GitHub Actions workflow
 */
async function triggerGitHubWorkflow(refreshType) {
  const githubToken = GITHUB_TOKEN;  // From environment variable
  
  if (!githubToken) {
    throw new Error('GitHub token not configured');
  }
  
  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${GITHUB_WORKFLOW_FILE}/dispatches`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${githubToken}`,
      'Accept': 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
      'User-Agent': 'CloudFlare-Worker'
    },
    body: JSON.stringify({
      ref: 'main',
      inputs: {
        refresh_type: refreshType,
        environment: 'production',
        date_range: getDateRange(refreshType)
      }
    })
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`GitHub API error: ${response.status} - ${error}`);
  }
  
  // Get the workflow run ID
  const runsUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runs?per_page=1`;
  const runsResponse = await fetch(runsUrl, {
    headers: {
      'Authorization': `Bearer ${githubToken}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'CloudFlare-Worker'
    }
  });
  
  const runs = await runsResponse.json();
  return {
    run_id: runs.workflow_runs[0]?.id,
    run_url: runs.workflow_runs[0]?.html_url
  };
}

/**
 * Get workflow status
 */
async function getWorkflowStatus() {
  const githubToken = GITHUB_TOKEN;
  
  if (!githubToken) {
    return { error: 'GitHub token not configured' };
  }
  
  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runs?per_page=5`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${githubToken}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'CloudFlare-Worker'
    }
  });
  
  if (!response.ok) {
    return { error: `GitHub API error: ${response.status}` };
  }
  
  const data = await response.json();
  
  return {
    recent_runs: data.workflow_runs.map(run => ({
      id: run.id,
      status: run.status,
      conclusion: run.conclusion,
      created_at: run.created_at,
      updated_at: run.updated_at,
      html_url: run.html_url
    }))
  };
}

/**
 * Determine date range based on refresh type
 */
function getDateRange(refreshType) {
  const now = new Date();
  const today = now.toISOString().split('T')[0];
  
  switch (refreshType) {
    case 'morning':
      // Full refresh: 7 days back for stat corrections
      const weekAgo = new Date(now);
      weekAgo.setDate(weekAgo.getDate() - 7);
      return `${weekAgo.toISOString().split('T')[0]},${today}`;
      
    case 'afternoon':
    case 'night':
      // Incremental refresh: 3 days back for lineup changes
      const threeDaysAgo = new Date(now);
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
      return `${threeDaysAgo.toISOString().split('T')[0]},${today}`;
      
    default:
      // Default: 2 days back
      const twoDaysAgo = new Date(now);
      twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);
      return `${twoDaysAgo.toISOString().split('T')[0]},${today}`;
  }
}

/**
 * Send notifications to configured webhooks
 */
async function sendNotifications(data) {
  const promises = [];
  
  // Slack notification
  if (typeof SLACK_WEBHOOK_URL !== 'undefined') {
    promises.push(sendSlackNotification(data));
  }
  
  // Discord notification
  if (typeof DISCORD_WEBHOOK_URL !== 'undefined') {
    promises.push(sendDiscordNotification(data));
  }
  
  // Wait for all notifications to complete
  await Promise.allSettled(promises);
}

/**
 * Send Slack notification
 */
async function sendSlackNotification(data) {
  const color = data.type === 'refresh_failed' ? 'danger' : 'good';
  const title = data.type === 'refresh_failed' 
    ? `❌ Data Refresh Failed`
    : `✅ Data Refresh Started`;
  
  const payload = {
    attachments: [{
      color,
      title,
      fields: [
        {
          title: 'Refresh Type',
          value: data.refreshType,
          short: true
        },
        {
          title: 'Timestamp',
          value: data.timestamp,
          short: true
        }
      ],
      footer: 'GKL Fantasy Analytics'
    }]
  };
  
  if (data.error) {
    payload.attachments[0].fields.push({
      title: 'Error',
      value: data.error,
      short: false
    });
  }
  
  if (data.workflowRun) {
    payload.attachments[0].fields.push({
      title: 'Workflow Run',
      value: `<https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runs/${data.workflowRun}|View on GitHub>`,
      short: false
    });
  }
  
  await fetch(SLACK_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

/**
 * Send Discord notification
 */
async function sendDiscordNotification(data) {
  const color = data.type === 'refresh_failed' ? 0xFF0000 : 0x00FF00;
  const title = data.type === 'refresh_failed' 
    ? '❌ Data Refresh Failed'
    : '✅ Data Refresh Started';
  
  const embed = {
    title,
    color,
    fields: [
      {
        name: 'Refresh Type',
        value: data.refreshType,
        inline: true
      },
      {
        name: 'Timestamp',
        value: data.timestamp,
        inline: true
      }
    ],
    footer: {
      text: 'GKL Fantasy Analytics'
    }
  };
  
  if (data.error) {
    embed.fields.push({
      name: 'Error',
      value: data.error,
      inline: false
    });
  }
  
  if (data.workflowRun) {
    embed.fields.push({
      name: 'Workflow Run',
      value: `[View on GitHub](https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runs/${data.workflowRun})`,
      inline: false
    });
  }
  
  await fetch(DISCORD_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ embeds: [embed] })
  });
}