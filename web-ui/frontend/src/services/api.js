const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://gkl-fantasy-api.services-403.workers.dev';

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
    const endpoint = `/transactions${queryString ? `?${queryString}` : ''}`;
    return this.request(endpoint);
  }

  async getTransactionStats() {
    return this.request('/transactions/stats');
  }

  async getTransactionFilters() {
    return this.request('/transactions/filters');
  }

  async searchPlayers(query) {
    const queryString = new URLSearchParams({ q: query }).toString();
    return this.request(`/transactions/players/search?${queryString}`);
  }

  // Analytics methods
  async getAnalyticsSummary() {
    return this.request('/analytics/summary');
  }

  async getManagerAnalytics() {
    return this.request('/analytics/managers');
  }

  // Health check
  async getHealth() {
    return this.request('/health');
  }

  // Lineup methods
  async getLineupDates() {
    return this.request('/lineups/dates');
  }

  async getTeams() {
    return this.request('/lineups/teams');
  }

  async getLineupsByDate(date) {
    return this.request(`/lineups/date/${date}`);
  }


  async getPlayerHistory(playerId, startDate, endDate) {
    const params = {};
    if (startDate) params.startDate = startDate;
    if (endDate) params.endDate = endDate;
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/lineups/player/${playerId}${queryString ? `?${queryString}` : ''}`);
  }

  async getLineupSummary(date) {
    return this.request(`/lineups/summary/${date}`);
  }

  async searchLineupPlayers(query) {
    const queryString = new URLSearchParams({ q: query }).toString();
    return this.request(`/lineups/search?${queryString}`);
  }

  // Player Spotlight methods
  async getPlayerSpotlight(playerId, season = 2025) {
    const params = { season };
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/players/${playerId}/spotlight?${queryString}`);
  }

  async getPlayerTimeline(playerId, season = 2025, granularity = 'day') {
    const params = { season, granularity };
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/players/${playerId}/timeline?${queryString}`);
  }

  async getPlayerSeasons(playerId) {
    return this.request(`/players/${playerId}/seasons`);
  }

  async searchSpotlightPlayers(query) {
    const params = { q: query };
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/players/search?${queryString}`);
  }

  async getPlayerPerformanceBreakdown(playerId, season = 2025) {
    const params = { season };
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/players/${playerId}/performance-breakdown?${queryString}`);
  }

  // Player Explorer endpoints
  async searchPlayersExplorer(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/player-search/search?${queryString}`);
  }
  
  // Alias for backward compatibility
  async searchPlayers(params = {}) {
    return this.searchPlayersExplorer(params);
  }

  async getPositions() {
    return this.request('/player-search/positions');
  }

  async getMlbTeams() {
    return this.request('/player-search/teams');
  }

  async getGklTeams() {
    return this.request('/player-search/gkl-teams');
  }
}

export default new ApiService();