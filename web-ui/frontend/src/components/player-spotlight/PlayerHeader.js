import React from 'react';

const PlayerHeader = ({ 
  player, 
  availableSeasons, 
  currentSeason, 
  onSeasonChange, 
  onBackClick 
}) => {
  const getPositionTypeLabel = (positionType) => {
    switch (positionType) {
      case 'B': return 'Batter';
      case 'P': return 'Pitcher';
      default: return positionType;
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'dtd': return 'text-yellow-600 bg-yellow-100';
      case 'il10':
      case 'il15':
      case 'il60': return 'text-red-600 bg-red-100';
      case 'na': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-800 bg-gray-100';
    }
  };

  const getStatusLabel = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy': return 'Healthy';
      case 'dtd': return 'Day-to-Day';
      case 'il10': return 'IL-10';
      case 'il15': return 'IL-15';
      case 'il60': return 'IL-60';
      case 'na': return 'Not Available';
      default: return status || 'Unknown';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-8">
      <div className="px-6 py-4">
        {/* Breadcrumb and Back Button */}
        <div className="flex items-center mb-4">
          <button
            onClick={onBackClick}
            className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
          >
            <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Daily Lineups
          </button>
        </div>

        {/* Main Header Content */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <div className="flex-1 min-w-0">
            {/* Player Name and Basic Info */}
            <div className="flex items-start space-x-4">
              <div className="flex-1">
                {/* Player Name with Status Badge */}
                <div className="flex items-end space-x-3 mb-1">
                  <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 truncate">
                    {player.player_name}
                  </h1>
                  {/* Player Status Badge - aligned to baseline */}
                  {player.player_status && (
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(player.player_status)}`}>
                      {getStatusLabel(player.player_status)}
                    </div>
                  )}
                </div>
                
                <div className="flex flex-col sm:flex-row sm:flex-wrap sm:space-x-4">
                  <div className="flex items-center text-gray-600">
                    <span className="font-medium">{player.player_team}</span>
                    <span className="mx-2">•</span>
                    <span>{getPositionTypeLabel(player.position_type)}</span>
                    <span className="mx-2">•</span>
                    <span className="text-gray-600">
                      {player.current_fantasy_team ? 
                        `Currently on: ${player.current_fantasy_team}` : 
                        'Not Currently Rostered'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Eligible Positions */}
            {player.eligible_positions && (
              <div className="mt-3">
                <span className="text-sm text-gray-500 mr-2">Eligible Positions:</span>
                <div className="inline-flex flex-wrap gap-1">
                  {typeof player.eligible_positions === 'string' ? 
                    player.eligible_positions.split(',').map((pos, index) => (
                      <span 
                        key={index}
                        className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium"
                      >
                        {pos.trim()}
                      </span>
                    )) : (
                      <span className="text-sm text-gray-500">No positions available</span>
                    )
                  }
                </div>
              </div>
            )}

            {/* Draft Information - NEW SECTION */}
            {player.draft_info && (
              <div className="flex flex-wrap items-center gap-x-2 text-gray-600 mt-2">
                {player.draft_info.draft_cost > 0 && (
                  <>
                    <span className="font-medium">
                      Draft: ${player.draft_info.draft_cost}
                    </span>
                    <span className="hidden sm:inline">•</span>
                  </>
                )}
                {player.draft_info.keeper_status && (
                  <>
                    <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded-full text-xs font-medium">
                      Keeper
                    </span>
                    <span className="hidden sm:inline">•</span>
                  </>
                )}
                <span className="text-sm sm:text-base">
                  Round {player.draft_info.draft_round}, Pick {player.draft_info.draft_pick}
                </span>
                <span className="hidden sm:inline">•</span>
                <span className="text-sm sm:text-base">
                  Drafted by: {player.draft_info.drafted_by}
                </span>
              </div>
            )}

            {/* Undrafted case */}
            {!player.draft_info && (
              <div className="text-gray-500 text-sm mt-2">
                Undrafted in {currentSeason}
              </div>
            )}

            {/* Team History */}
            {player.team_history && player.team_history.length > 1 && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <span className="text-sm text-gray-500 mr-2">Team History in {currentSeason}:</span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {player.team_history.slice().reverse().map((team, index) => (
                    <div
                      key={index}
                      className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${
                        team.team_name === player.current_fantasy_team
                          ? 'bg-blue-100 text-blue-800 font-medium border border-blue-200'
                          : 'bg-gray-100 text-gray-700 border border-gray-200'
                      }`}
                    >
                      <span>{team.team_name}</span>
                      <span className="ml-2 text-xs opacity-75">
                        {team.days} days ({team.percentage.toFixed(0)}%)
                      </span>
                      {team.team_name === player.current_fantasy_team && (
                        <span className="ml-2 text-xs font-medium">(Current)</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Season Selector */}
          <div className="mt-4 sm:mt-0 sm:ml-4">
            <div className="flex items-center space-x-2">
              <label htmlFor="season-select" className="text-sm font-medium text-gray-700">
                Season:
              </label>
              <select
                id="season-select"
                value={currentSeason}
                onChange={(e) => onSeasonChange(parseInt(e.target.value))}
                className="form-select text-sm"
              >
                {availableSeasons && availableSeasons.length > 0 ? (
                  availableSeasons.map(season => (
                    <option key={season.season} value={season.season}>
                      {season.season} ({season.total_days} days)
                    </option>
                  ))
                ) : (
                  <option value={currentSeason}>{currentSeason}</option>
                )}
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlayerHeader;