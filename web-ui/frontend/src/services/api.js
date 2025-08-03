const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001';

class ApiService {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Transaction methods
  async getTransactions(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const endpoint = `/api/transactions${queryString ? `?${queryString}` : ''}`;
    return this.request(endpoint);
  }

  async getTransactionStats() {
    return this.request('/api/transactions/stats');
  }

  async getTransactionFilters() {
    return this.request('/api/transactions/filters');
  }

  async searchPlayers(query) {
    const queryString = new URLSearchParams({ q: query }).toString();
    return this.request(`/api/transactions/players/search?${queryString}`);
  }

  // Analytics methods
  async getAnalyticsSummary() {
    return this.request('/api/analytics/summary');
  }

  async getManagerAnalytics() {
    return this.request('/api/analytics/managers');
  }

  // Health check
  async getHealth() {
    return this.request('/health');
  }

  // Lineup methods
  async getLineupDates() {
    return this.request('/api/lineups/dates');
  }

  async getTeams() {
    return this.request('/api/lineups/teams');
  }

  async getLineupsByDate(date) {
    return this.request(`/api/lineups/date/${date}`);
  }

  async getTeamLineup(date, teamKey) {
    return this.request(`/api/lineups/date/${date}/team/${teamKey}`);
  }

  async getPlayerHistory(playerId, startDate, endDate) {
    const params = {};
    if (startDate) params.startDate = startDate;
    if (endDate) params.endDate = endDate;
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/api/lineups/player/${playerId}${queryString ? `?${queryString}` : ''}`);
  }

  async getLineupSummary(date) {
    return this.request(`/api/lineups/summary/${date}`);
  }

  async searchLineupPlayers(query) {
    const queryString = new URLSearchParams({ q: query }).toString();
    return this.request(`/api/lineups/search?${queryString}`);
  }
}

export default new ApiService();