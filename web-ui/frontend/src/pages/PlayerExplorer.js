import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiService from '../services/api';
import PositionFilter from '../components/PositionFilter';

const PlayerExplorer = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    position: '',
    mlbTeam: '',
    gklTeam: ''
  });
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [availableFilters, setAvailableFilters] = useState({
    positions: [],
    mlbTeams: [],
    gklTeams: []
  });
  const [hasSearched, setHasSearched] = useState(false);

  // Fetch filter options on mount
  useEffect(() => {
    const fetchFilterOptions = async () => {
      try {
        const [positionsData, mlbTeamsData, gklTeamsData] = await Promise.all([
          apiService.getPositions(),
          apiService.getMlbTeams(),
          apiService.getGklTeams()
        ]);
        console.log('Filter options loaded:', {
          positions: positionsData,
          mlbTeams: mlbTeamsData?.length,
          gklTeams: gklTeamsData?.length
        });
        setAvailableFilters({
          positions: positionsData || [],
          mlbTeams: mlbTeamsData || [],
          gklTeams: gklTeamsData || []
        });
      } catch (error) {
        console.error('Failed to fetch filter options:', error);
      }
    };
    fetchFilterOptions();
  }, []);

  // Search function (uses current state)
  const searchPlayers = async (pageNum = currentPage) => {
    await searchPlayersWithFilters(filters, searchTerm, pageNum);
  };

  // Initial search on mount
  useEffect(() => {
    searchPlayers(1);
  }, []); // Run once on mount

  // Handle search on Enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      setCurrentPage(1);
      searchPlayers(1);
    }
  };

  // Handle filter changes and trigger search
  const handleFilterChange = (filterName, value) => {
    const newFilters = { ...filters, [filterName]: value };
    setFilters(newFilters);
    setCurrentPage(1);
    
    // Immediately search with new filters
    searchPlayersWithFilters(newFilters, searchTerm, 1);
  };

  // Search function that accepts explicit parameters
  const searchPlayersWithFilters = async (filtersToUse, searchToUse, pageNum) => {
    setLoading(true);
    setError(null);
    setHasSearched(true);
    
    try {
      const response = await apiService.searchPlayers({
        search: searchToUse,
        ...filtersToUse,
        page: pageNum,
        limit: 20
      });
      console.log('Search response:', response);
      setPlayers(response.players || []);
      setTotalCount(response.total || 0);
    } catch (err) {
      setError('Failed to search players. Please try again.');
      console.error('Search error:', err);
      setPlayers([]);
    } finally {
      setLoading(false);
    }
  };

  // Handle search term change
  const handleSearchChange = (value) => {
    setSearchTerm(value);
    setCurrentPage(1);
    // Immediately search with new term
    searchPlayersWithFilters(filters, value, 1);
  };

  // Reset all filters and search
  const resetFilters = () => {
    const emptyFilters = {
      position: '',
      mlbTeam: '',
      gklTeam: ''
    };
    setSearchTerm('');
    setFilters(emptyFilters);
    setCurrentPage(1);
    // Immediately search with empty filters
    searchPlayersWithFilters(emptyFilters, '', 1);
  };

  // Navigate to player spotlight
  const viewPlayerCard = (playerId) => {
    navigate(`/lineups/player/${playerId}`);
  };

  // Get status badge color
  const getStatusBadgeColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'rostered':
        return 'bg-green-100 text-green-800';
      case 'free agent':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Handle pagination
  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    searchPlayers(newPage);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Player Explorer</h1>
          <p className="text-gray-600 mt-1">
            Search and explore player statistics, transaction history, and usage patterns
          </p>
        </div>
      </div>

      {/* Filters Card - Similar to Transactions page */}
      <div className="card">
        <div className="card-header">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-gray-900">Filters</h3>
            <button
              onClick={resetFilters}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              Reset All
            </button>
          </div>
        </div>
        <div className="card-body">
          {/* First row of filters */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {/* Player Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Player Search
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Search players..."
                className="form-input"
              />
            </div>

            {/* Fantasy Team Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fantasy Team
              </label>
              <select
                value={filters.gklTeam}
                onChange={(e) => handleFilterChange('gklTeam', e.target.value)}
                className="form-select"
              >
                <option value="">All Teams</option>
                {availableFilters.gklTeams.map(team => (
                  <option key={team} value={team}>{team}</option>
                ))}
              </select>
            </div>

            {/* MLB Team Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                MLB Team
              </label>
              <select
                value={filters.mlbTeam}
                onChange={(e) => handleFilterChange('mlbTeam', e.target.value)}
                className="form-select"
              >
                <option value="">All MLB Teams</option>
                {availableFilters.mlbTeams.map(team => (
                  <option key={team} value={team}>{team}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Position Filter - Using the button-based component */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Position
            </label>
            <PositionFilter
              selectedPositions={filters.position || ''}
              availablePositions={availableFilters.positions || []}
              onChange={(value) => handleFilterChange('position', value)}
            />
          </div>

          {/* Results count */}
          <div className="mt-4 text-sm text-gray-600">
            {!loading && hasSearched && (
              <span>{totalCount} {totalCount === 1 ? 'player' : 'players'}</span>
            )}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Searching players...</p>
        </div>
      )}

      {/* Results Grid */}
      {!loading && players.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {players.map((player) => (
              <div key={player.player_id} className="card hover:shadow-lg transition-shadow">
                <div className="card-body">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {player.player_name}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {player.position} • {player.mlb_team}
                        {player.health_status && player.health_status !== 'healthy' && (
                          <span className="ml-1 text-orange-600 font-medium">
                            ({player.health_status})
                          </span>
                        )}
                      </p>
                    </div>
                    {player.roster_status && (
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(player.roster_status)}`}>
                        {player.roster_status}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                    <div>
                      <p className="text-gray-500">Transactions</p>
                      <p className="font-semibold text-gray-900">{player.transaction_count || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Days Rostered</p>
                      <p className="font-semibold text-gray-900">{Math.round(player.days_rostered) || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Times Added</p>
                      <p className="font-semibold text-gray-900">{player.times_added || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Times Dropped</p>
                      <p className="font-semibold text-gray-900">{player.times_dropped || 0}</p>
                    </div>
                  </div>

                  {player.most_recent_team && (
                    <div className="mb-3 pb-3 border-b border-gray-200">
                      <p className="text-sm text-gray-500">Most Recent Fantasy Team</p>
                      <p className="text-sm font-medium text-gray-900">{player.most_recent_team}</p>
                    </div>
                  )}

                  <button
                    onClick={() => viewPlayerCard(player.player_id)}
                    className="btn-primary w-full"
                  >
                    View Player Card
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalCount > 20 && (
            <div className="flex justify-center mt-6">
              <nav className="flex space-x-2">
                <button
                  onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1 || loading}
                  className="btn-secondary"
                >
                  Previous
                </button>
                <span className="flex items-center px-4 text-gray-700">
                  Page {currentPage} of {Math.ceil(totalCount / 20)}
                </span>
                <button
                  onClick={() => handlePageChange(Math.min(Math.ceil(totalCount / 20), currentPage + 1))}
                  disabled={currentPage >= Math.ceil(totalCount / 20) || loading}
                  className="btn-secondary"
                >
                  Next
                </button>
              </nav>
            </div>
          )}
        </>
      )}

      {/* Empty State - No Results */}
      {!loading && hasSearched && players.length === 0 && !error && (
        <div className="card">
          <div className="card-body text-center py-12">
            <div className="text-4xl mb-4">🤷</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Players Found
            </h3>
            <p className="text-gray-600">
              Try adjusting your search criteria or filters
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlayerExplorer;