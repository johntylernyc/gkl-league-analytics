import React, { useState } from 'react';
import { useLineups } from '../hooks/useLineups';
import DateNavigator from '../components/lineups/DateNavigator';
import TeamSelector from '../components/lineups/TeamSelector';
import LineupGrid from '../components/lineups/LineupGrid';
import PlayerDetailsModal from '../components/lineups/PlayerDetailsModal';

const DailyLineups = () => {
  const {
    lineups,
    teams,
    availableDates,
    selectedDate,
    selectedTeam,
    loading,
    error,
    summary,
    setSelectedDate,
    setSelectedTeam,
    goToPreviousDate,
    goToNextDate,
    canGoNext,
    canGoPrevious
  } = useLineups();

  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handlePlayerClick = (player) => {
    setSelectedPlayer(player);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedPlayer(null);
  };

  if (error && !loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Daily Lineups</h1>
        <div className="card">
          <div className="card-body text-center py-12">
            <div className="text-red-400 text-5xl mb-4">⚠️</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Lineups</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="btn-primary"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daily Lineups</h1>
          <p className="text-gray-600 mt-1">
            View and analyze daily lineup decisions
          </p>
        </div>
        {loading && (
          <div className="flex items-center text-sm text-gray-500">
            <svg className="h-4 w-4 mr-1 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Loading...
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="space-y-4">
        <DateNavigator
          selectedDate={selectedDate}
          availableDates={availableDates}
          onDateChange={setSelectedDate}
          onPrevious={goToPreviousDate}
          onNext={goToNextDate}
          canGoPrevious={canGoPrevious}
          canGoNext={canGoNext}
        />
        
        <TeamSelector
          teams={teams}
          selectedTeam={selectedTeam}
          onTeamChange={setSelectedTeam}
        />
      </div>

      {/* Summary Stats */}
      {summary && !selectedTeam && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card">
            <div className="card-body text-center">
              <div className="text-2xl font-bold text-primary-600">
                {summary.teams || 0}
              </div>
              <div className="text-sm text-gray-500">Teams</div>
            </div>
          </div>
          <div className="card">
            <div className="card-body text-center">
              <div className="text-2xl font-bold text-success-600">
                {summary.unique_players || 0}
              </div>
              <div className="text-sm text-gray-500">Unique Players</div>
            </div>
          </div>
          <div className="card">
            <div className="card-body text-center">
              <div className="text-2xl font-bold text-warning-600">
                {summary.benched || 0}
              </div>
              <div className="text-sm text-gray-500">Benched</div>
            </div>
          </div>
          <div className="card">
            <div className="card-body text-center">
              <div className="text-2xl font-bold text-red-600">
                {summary.injured || 0}
              </div>
              <div className="text-sm text-gray-500">IL/NA</div>
            </div>
          </div>
        </div>
      )}

      {/* Lineups Display */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="text-center">
            <svg className="h-8 w-8 mx-auto text-gray-400 animate-spin mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <p className="text-gray-500">Loading lineup data...</p>
          </div>
        </div>
      ) : lineups.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {lineups.map((lineup, index) => (
            <LineupGrid
              key={`${lineup.team_key}-${index}`}
              lineup={lineup}
              onPlayerClick={handlePlayerClick}
            />
          ))}
        </div>
      ) : (
        <div className="card">
          <div className="card-body text-center py-12">
            <div className="text-gray-300 text-6xl mb-4">📋</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Lineup Data Available
            </h3>
            <p className="text-gray-600">
              {selectedDate 
                ? `No lineup data found for ${selectedDate}`
                : 'Please select a date to view lineups'}
            </p>
          </div>
        </div>
      )}

      {/* Most Started Players (when viewing all teams) */}
      {summary && summary.most_started && summary.most_started.length > 0 && !selectedTeam && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Most Started Players</h3>
            <p className="text-sm text-gray-500 mt-1">Players started by multiple teams on {selectedDate}</p>
          </div>
          <div className="card-body">
            <div className="space-y-2">
              {summary.most_started.map((player, index) => (
                <div key={player.player_id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <span className="text-sm font-medium text-gray-900">
                    {index + 1}. {player.player_name}
                  </span>
                  <span className="text-sm text-gray-500">
                    Started by {player.times_started} teams
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Player Details Modal */}
      <PlayerDetailsModal
        player={selectedPlayer}
        isOpen={isModalOpen}
        onClose={closeModal}
        currentDate={selectedDate}
      />
    </div>
  );
};

export default DailyLineups;