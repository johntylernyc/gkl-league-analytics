import React from 'react';
import PlayerCard from './PlayerCard';

const LineupGrid = ({ lineup, onPlayerClick }) => {
  if (!lineup || !lineup.players) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-center text-gray-500">No lineup data available</p>
      </div>
    );
  }

  // Group players by position type and status
  const groupedPlayers = {
    batters: [],
    pitchers: [],
    bench: [],
    injured: []
  };

  lineup.players.forEach(player => {
    if (['IL', 'IL10', 'IL60', 'NA'].includes(player.selected_position)) {
      groupedPlayers.injured.push(player);
    } else if (player.selected_position === 'BN') {
      groupedPlayers.bench.push(player);
    } else if (['SP', 'RP', 'P'].includes(player.selected_position)) {
      groupedPlayers.pitchers.push(player);
    } else {
      groupedPlayers.batters.push(player);
    }
  });

  // Sort batters by position order
  const positionOrder = ['C', '1B', '2B', '3B', 'SS', 'MI', 'CI', 'OF', 'LF', 'CF', 'RF', 'Util', 'UTIL'];
  groupedPlayers.batters.sort((a, b) => {
    const aIndex = positionOrder.indexOf(a.selected_position);
    const bIndex = positionOrder.indexOf(b.selected_position);
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
  });

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">
          {lineup.team_name}
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {lineup.date}
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Starting Batters */}
        {groupedPlayers.batters.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">
              Starting Lineup - Batters ({groupedPlayers.batters.length})
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {groupedPlayers.batters.map((player, index) => (
                <PlayerCard 
                  key={`${player.player_id}-${index}`} 
                  player={player} 
                  onClick={onPlayerClick}
                />
              ))}
            </div>
          </div>
        )}

        {/* Starting Pitchers */}
        {groupedPlayers.pitchers.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">
              Starting Lineup - Pitchers ({groupedPlayers.pitchers.length})
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {groupedPlayers.pitchers.map((player, index) => (
                <PlayerCard 
                  key={`${player.player_id}-${index}`} 
                  player={player} 
                  onClick={onPlayerClick}
                />
              ))}
            </div>
          </div>
        )}

        {/* Bench */}
        {groupedPlayers.bench.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">
              Bench ({groupedPlayers.bench.length})
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {groupedPlayers.bench.map((player, index) => (
                <PlayerCard 
                  key={`${player.player_id}-${index}`} 
                  player={player} 
                  onClick={onPlayerClick}
                />
              ))}
            </div>
          </div>
        )}

        {/* Injured/NA */}
        {groupedPlayers.injured.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">
              Injured List / Not Active ({groupedPlayers.injured.length})
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {groupedPlayers.injured.map((player, index) => (
                <PlayerCard 
                  key={`${player.player_id}-${index}`} 
                  player={player} 
                  onClick={onPlayerClick}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Summary Stats */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <div className="flex justify-around text-xs text-gray-600">
          <span>Total: {lineup.players.length} players</span>
          <span>Active: {groupedPlayers.batters.length + groupedPlayers.pitchers.length}</span>
          <span>Bench: {groupedPlayers.bench.length}</span>
          <span>IL/NA: {groupedPlayers.injured.length}</span>
        </div>
      </div>
    </div>
  );
};

export default LineupGrid;