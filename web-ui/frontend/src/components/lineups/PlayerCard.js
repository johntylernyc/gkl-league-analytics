import React from 'react';

const PlayerCard = ({ player, onClick }) => {
  // Determine status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-50';
      case 'DTD':
        return 'text-yellow-600 bg-yellow-50';
      case 'IL':
      case 'IL10':
      case 'IL60':
        return 'text-red-600 bg-red-50';
      case 'NA':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  // Determine position type color
  const getPositionColor = (position) => {
    if (['SP', 'RP', 'P'].includes(position)) {
      return 'bg-blue-100 text-blue-800';
    } else if (['BN', 'IL', 'IL10', 'IL60', 'NA'].includes(position)) {
      return 'bg-gray-100 text-gray-800';
    } else {
      return 'bg-green-100 text-green-800';
    }
  };

  return (
    <div 
      className="bg-white rounded-lg border border-gray-200 p-3 hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onClick && onClick(player)}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getPositionColor(player.selected_position)}`}>
              {player.selected_position}
            </span>
            {player.player_status && player.player_status !== 'healthy' && (
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(player.player_status)}`}>
                {player.player_status}
              </span>
            )}
          </div>
          <h4 className="mt-1 text-sm font-medium text-gray-900 truncate">
            {player.player_name}
          </h4>
          {player.player_team && (
            <p className="text-xs text-gray-500 mt-0.5">
              {player.player_team}
            </p>
          )}
        </div>
      </div>
      
      {player.eligible_positions && player.eligible_positions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {(typeof player.eligible_positions === 'string' 
            ? player.eligible_positions.split(',') 
            : player.eligible_positions
          ).map(pos => (
            <span 
              key={pos} 
              className="inline-flex items-center px-1.5 py-0.5 rounded text-xs text-gray-600 bg-gray-100"
            >
              {pos}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default PlayerCard;