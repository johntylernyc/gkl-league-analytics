import React, { useState, useEffect } from 'react';
import api from '../../services/api';

const PlayerDetailsModal = ({ player, isOpen, onClose, currentDate }) => {
  const [playerHistory, setPlayerHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && player) {
      fetchPlayerHistory();
    }
  }, [isOpen, player]);

  const fetchPlayerHistory = async () => {
    if (!player?.player_id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const history = await api.getPlayerHistory(player.player_id);
      setPlayerHistory(history);
    } catch (err) {
      console.error('Error fetching player history:', err);
      setError('Failed to load player history');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !player) return null;

  const getPositionTypeLabel = (positionType) => {
    switch (positionType) {
      case 'B': return 'Batter';
      case 'P': return 'Pitcher';
      default: return positionType;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-600';
      case 'DTD': return 'text-yellow-600';
      case 'IL10':
      case 'IL15':
      case 'IL60': return 'text-red-600';
      case 'NA': return 'text-gray-600';
      default: return 'text-gray-800';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'healthy': return 'Healthy';
      case 'DTD': return 'Day-to-Day';
      case 'IL10': return 'IL-10';
      case 'IL15': return 'IL-15';
      case 'IL60': return 'IL-60';
      case 'NA': return 'Not Available';
      default: return status;
    }
  };

  const getPositionColor = (position) => {
    if (['BN', 'IL', 'IL10', 'IL15', 'IL60', 'NA'].includes(position)) {
      return 'bg-gray-100 text-gray-600';
    }
    return 'bg-blue-100 text-blue-800';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-primary-600 text-white p-6 flex justify-between items-start">
          <div>
            <h2 className="text-xl font-bold">{player.player_name}</h2>
            <p className="text-primary-100 mt-1">
              {player.player_team} • {getPositionTypeLabel(player.position_type)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-primary-100 hover:text-white transition-colors"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* Current Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Current Status</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Position:</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getPositionColor(player.selected_position)}`}>
                    {player.selected_position}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span className={`font-medium ${getStatusColor(player.player_status)}`}>
                    {getStatusLabel(player.player_status)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Team:</span>
                  <span className="font-medium">{player.player_team}</span>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Eligible Positions</h3>
              <div className="flex flex-wrap gap-1">
                {player.eligible_positions && typeof player.eligible_positions === 'string' ? (
                  player.eligible_positions.split(',').map((pos, index) => (
                    <span 
                      key={index}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium"
                    >
                      {pos.trim()}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-500">No positions available</span>
                )}
              </div>
            </div>
          </div>

          {/* Player History */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage History</h3>
            
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <svg className="h-6 w-6 text-gray-400 animate-spin mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="text-gray-600">Loading history...</span>
              </div>
            ) : error ? (
              <div className="text-center py-8">
                <p className="text-red-600">{error}</p>
                <button 
                  onClick={fetchPlayerHistory}
                  className="mt-2 text-sm text-primary-600 hover:text-primary-800"
                >
                  Try Again
                </button>
              </div>
            ) : playerHistory ? (
              <div className="space-y-4">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
                  <div className="text-center">
                    <div className="text-lg font-bold text-gray-900">{playerHistory.stats.total_days}</div>
                    <div className="text-xs text-gray-500">Total Days</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-green-600">{playerHistory.stats.games_started}</div>
                    <div className="text-xs text-gray-500">Started</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-yellow-600">{playerHistory.stats.games_benched}</div>
                    <div className="text-xs text-gray-500">Benched</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-red-600">{playerHistory.stats.games_injured}</div>
                    <div className="text-xs text-gray-500">IL/NA</div>
                  </div>
                </div>

                {/* Recent History */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Recent Activity (Last 10 Days)</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {playerHistory.history.slice(0, 10).map((day, index) => (
                      <div 
                        key={index}
                        className={`flex justify-between items-center p-3 rounded border ${
                          day.date === currentDate ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-200'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-sm font-medium text-gray-900">{day.date}</span>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getPositionColor(day.selected_position)}`}>
                            {day.selected_position}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-600">{day.team_name}</div>
                          <div className={`text-xs ${getStatusColor(day.player_status)}`}>
                            {getStatusLabel(day.player_status)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-3 flex justify-end">
          <button
            onClick={onClose}
            className="btn-secondary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default PlayerDetailsModal;