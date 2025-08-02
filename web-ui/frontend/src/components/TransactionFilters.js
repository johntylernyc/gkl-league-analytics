import React, { useState, useEffect } from 'react';
import apiService from '../services/api';
import PositionFilter from './PositionFilter';

const TransactionFilters = ({ filters, onFiltersChange, onReset }) => {
  const [availableFilters, setAvailableFilters] = useState({
    transactionTypes: [],
    movementTypes: [],
    teams: [],
    positions: [],
    mlbTeams: []
  });
  const [playerSearch, setPlayerSearch] = useState(filters.search || '');

  useEffect(() => {
    const fetchFilters = async () => {
      try {
        const data = await apiService.getTransactionFilters();
        setAvailableFilters(data);
      } catch (error) {
        console.error('Failed to fetch filter options:', error);
      }
    };
    fetchFilters();
  }, []);

  const handleFilterChange = (key, value) => {
    onFiltersChange({ [key]: value });
  };

  const handlePlayerSearchChange = (e) => {
    const value = e.target.value;
    setPlayerSearch(value);
    
    // Debounce search
    const timeoutId = setTimeout(() => {
      onFiltersChange({ search: value });
    }, 300);
    
    return () => clearTimeout(timeoutId);
  };

  const handleReset = () => {
    setPlayerSearch('');
    onReset();
  };

  return (
    <div className="card mb-6">
      <div className="card-header">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium text-gray-900">Filters</h3>
          <button
            onClick={handleReset}
            className="text-sm text-primary-600 hover:text-primary-700"
          >
            Reset All
          </button>
        </div>
      </div>
      <div className="card-body">
        {/* First row of filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {/* Player Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Player Search
            </label>
            <input
              type="text"
              value={playerSearch}
              onChange={handlePlayerSearchChange}
              placeholder="Search players..."
              className="form-input"
            />
          </div>

          {/* Transaction Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Transaction Type
            </label>
            <select
              value={filters.transactionType || ''}
              onChange={(e) => handleFilterChange('transactionType', e.target.value)}
              className="form-select"
            >
              <option value="">All Types</option>
              {(availableFilters.transactionTypes || []).map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          {/* Movement Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Movement Type
            </label>
            <select
              value={filters.movementType || ''}
              onChange={(e) => handleFilterChange('movementType', e.target.value)}
              className="form-select"
            >
              <option value="">All Movements</option>
              {(availableFilters.movementTypes || []).map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          {/* Team */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Fantasy Team
            </label>
            <select
              value={filters.teamName || ''}
              onChange={(e) => handleFilterChange('teamName', e.target.value)}
              className="form-select"
            >
              <option value="">All Teams</option>
              {(availableFilters.teams || []).map(team => (
                <option key={team} value={team}>{team}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Second row with MLB Team and Position filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* MLB Team */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              MLB Team
            </label>
            <select
              value={filters.playerTeam || ''}
              onChange={(e) => handleFilterChange('playerTeam', e.target.value)}
              className="form-select"
            >
              <option value="">All MLB Teams</option>
              {(availableFilters.mlbTeams || []).map(team => (
                <option key={team} value={team}>{team}</option>
              ))}
            </select>
          </div>

          {/* Position filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Position
            </label>
            <PositionFilter
              selectedPositions={filters.playerPosition || ''}
              availablePositions={availableFilters.positions || []}
              onChange={(value) => handleFilterChange('playerPosition', value)}
            />
          </div>
        </div>

        {/* Date Range */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={filters.startDate || ''}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
              className="form-input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={filters.endDate || ''}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
              className="form-input"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default TransactionFilters;