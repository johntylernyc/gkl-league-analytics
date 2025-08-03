import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import PlayerHeader from '../components/player-spotlight/PlayerHeader';
import UsageSummaryCards from '../components/player-spotlight/UsageSummaryCards';
import MonthlyTimeline from '../components/player-spotlight/MonthlyTimeline';
import PerformanceBreakdown from '../components/player-spotlight/PerformanceBreakdown';

const PlayerSpotlight = () => {
  const { playerId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [playerData, setPlayerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Get season from URL params or default to 2025
  const currentSeason = parseInt(searchParams.get('season')) || 2025;
  const currentDate = searchParams.get('date') || null;

  useEffect(() => {
    if (playerId) {
      fetchPlayerData();
    }
  }, [playerId, currentSeason]);

  const fetchPlayerData = async () => {
    if (!playerId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await api.getPlayerSpotlight(playerId, currentSeason);
      setPlayerData(data);
    } catch (err) {
      console.error('Error fetching player spotlight data:', err);
      setError('Failed to load player data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSeasonChange = (newSeason) => {
    setSearchParams(params => {
      params.set('season', newSeason.toString());
      return params;
    });
  };

  const handleBackClick = () => {
    const date = searchParams.get('date');
    if (date) {
      navigate(`/lineups?date=${date}`);
    } else {
      navigate('/lineups');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Loading skeleton */}
          <div className="animate-pulse">
            {/* Header skeleton */}
            <div className="mb-8">
              <div className="h-8 bg-gray-300 rounded w-64 mb-4"></div>
              <div className="h-6 bg-gray-200 rounded w-96"></div>
            </div>
            
            {/* Cards skeleton */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-white p-6 rounded-lg shadow">
                  <div className="h-4 bg-gray-200 rounded w-20 mb-2"></div>
                  <div className="h-8 bg-gray-300 rounded w-16 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-24"></div>
                </div>
              ))}
            </div>
            
            {/* Timeline skeleton */}
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="h-6 bg-gray-300 rounded w-48 mb-6"></div>
              <div className="space-y-4">
                {[...Array(6)].map((_, i) => (
                  <div key={i}>
                    <div className="h-4 bg-gray-200 rounded w-20 mb-2"></div>
                    <div className="h-6 bg-gray-300 rounded"></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <div className="text-red-600 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Player Data</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <div className="space-x-4">
              <button
                onClick={fetchPlayerData}
                className="btn-primary"
              >
                Try Again
              </button>
              <button
                onClick={handleBackClick}
                className="btn-secondary"
              >
                Back to Lineups
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!playerData) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Player Not Found</h3>
            <p className="text-gray-600 mb-4">The requested player could not be found.</p>
            <button
              onClick={handleBackClick}
              className="btn-primary"
            >
              Back to Lineups
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Player Header */}
        <PlayerHeader
          player={playerData.player}
          availableSeasons={playerData.available_seasons}
          currentSeason={currentSeason}
          onSeasonChange={handleSeasonChange}
          onBackClick={handleBackClick}
        />

        {/* Main Content */}
        <div className="space-y-8">

          {/* Usage Summary Cards */}
          <UsageSummaryCards
            usageBreakdown={playerData.usage_breakdown}
            monthlyData={playerData.monthly_data}
            season={currentSeason}
          />

          {/* Performance Breakdown */}
          <PerformanceBreakdown
            playerId={playerId}
            playerName={playerData.player.player_name}
            season={currentSeason}
          />

          {/* Monthly Timeline */}
          <MonthlyTimeline
            monthlyData={playerData.monthly_data}
            season={currentSeason}
            playerName={playerData.player.player_name}
          />

          {/* Data Quality Notice */}
          {playerData.data_completeness && !playerData.data_completeness.has_usage_data && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-blue-700">
                    📊 Timeline shows data through {playerData.data_completeness.latest_date || 'current date'}. 
                    Future dates will become available as the season progresses.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PlayerSpotlight;