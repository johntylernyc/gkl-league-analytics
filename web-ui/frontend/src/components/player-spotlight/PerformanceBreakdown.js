import React, { useState, useEffect } from 'react';
import api from '../../services/api';

const PerformanceBreakdown = ({ playerId, playerName, season }) => {
  const [performanceData, setPerformanceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedRows, setExpandedRows] = useState(new Set());
  
  const toggleRowExpansion = (usageType) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(usageType)) {
      newExpanded.delete(usageType);
    } else {
      newExpanded.add(usageType);
    }
    setExpandedRows(newExpanded);
  };

  // Fetch performance data
  useEffect(() => {
    const fetchPerformanceData = async () => {
      if (!playerId) return;
      
      try {
        setLoading(true);
        setError(null);
        
        const response = await api.getPlayerPerformanceBreakdown(playerId, season);
        setPerformanceData(response);
      } catch (err) {
        console.error('Error fetching performance data:', err);
        setError(err.response?.data?.message || 'Failed to load performance data');
      } finally {
        setLoading(false);
      }
    };

    fetchPerformanceData();
  }, [playerId, season]);

  // Format stat values based on type
  const formatStatValue = (stat, value) => {
    if (value === null || value === undefined) return '-';
    
    // Batting averages and percentages (3 decimal places)
    if (['AVG', 'OBP', 'SLG'].includes(stat)) {
      return value.toFixed(3);
    }
    
    // Pitching ratios
    if (['ERA', 'WHIP'].includes(stat)) {
      return value.toFixed(2);
    }
    
    if (stat === 'K/BB') {
      return value.toFixed(2);
    }
    
    // Whole numbers
    return value.toString();
  };

  // Get usage type colors
  const getUsageColor = (usageType) => {
    switch (usageType) {
      case 'started': return 'text-green-600 bg-green-50 border-green-200';
      case 'benched': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'injured_list': return 'text-red-600 bg-red-50 border-red-200';
      case 'other_roster': return 'text-purple-600 bg-purple-50 border-purple-200';
      case 'minor_leagues': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'not_rostered': return 'text-gray-600 bg-gray-50 border-gray-200';
      case 'not_owned': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  // Get usage type display names
  const getUsageTitle = (usageType) => {
    switch (usageType) {
      case 'started': return 'Started';
      case 'benched': return 'Benched';
      case 'injured_list': return 'Injured List';
      case 'other_roster': return 'On Another Roster';
      case 'minor_leagues': return 'Minor Leagues';
      case 'not_rostered': return 'Not Rostered';
      case 'not_owned': return 'Not Rostered';
      default: return usageType;
    }
  };

  // Get stat categories based on player type
  const getStatCategories = (playerType) => {
    if (playerType === 'pitcher') {
      return {
        stats: ['APP', 'W', 'SV', 'K', 'HLD', 'ERA', 'WHIP', 'K/BB', 'QS'],
        type: 'pitching'
      };
    } else if (playerType === 'batter') {
      return {
        stats: ['R', 'H', '3B', 'HR', 'RBI', 'SB', 'AVG', 'OBP', 'SLG'],
        type: 'batting'
      };
    } else if (playerType === 'both') {
      return {
        stats: ['R', 'H', '3B', 'HR', 'RBI', 'SB', 'AVG', 'OBP', 'SLG'],
        pitchingStats: ['APP', 'W', 'SV', 'K', 'HLD', 'ERA', 'WHIP', 'K/BB', 'QS'],
        type: 'both'
      };
    }
    
    // Default to batting
    return {
      stats: ['R', 'H', '3B', 'HR', 'RBI', 'SB', 'AVG', 'OBP', 'SLG'],
      type: 'batting'
    };
  };

  // Loading state
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Performance Breakdown
        </h2>
        <div className="text-center py-8">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mx-auto mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2 mx-auto"></div>
          </div>
          <p className="text-gray-600 mt-4">Loading performance data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Performance Breakdown
        </h2>
        <div className="text-center py-8">
          <div className="text-red-400 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-gray-600">Error loading performance data</p>
          <p className="text-sm text-gray-500 mt-2">{error}</p>
        </div>
      </div>
    );
  }

  // No data state
  if (!performanceData || !performanceData.usage_breakdown) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Performance Breakdown
        </h2>
        <div className="text-center py-8">
          <div className="text-gray-400 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="text-gray-600">No performance statistics available for {season} season</p>
        </div>
      </div>
    );
  }

  const { player_type, usage_breakdown } = performanceData;
  const statConfig = getStatCategories(player_type);
  const usageTypes = ['started', 'benched', 'injured_list', 'minor_leagues', 'other_roster', 'not_rostered', 'not_owned'];

  // Filter to only show usage types that have data
  const availableUsageTypes = usageTypes.filter(usageType => 
    usage_breakdown[usageType] && usage_breakdown[usageType].days > 0
  );

  if (availableUsageTypes.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Performance Breakdown
        </h2>
        <div className="text-center py-8">
          <p className="text-gray-600">No roster usage data available for statistics analysis</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          {statConfig.type === 'pitching' ? 'Pitching Performance Breakdown' : 
           statConfig.type === 'both' ? 'Performance Breakdown' : 'Batting Performance Breakdown'}
        </h2>
        <p className="text-gray-600">
          {playerName}'s statistical performance across different roster situations in {season}
        </p>
        {player_type === 'both' && (
          <p className="text-sm text-blue-600 mt-1">
            Two-way player - showing batting statistics (pitching stats available in separate view)
          </p>
        )}
      </div>

      {/* Comparison Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Days
              </th>
              {statConfig.stats.map(stat => (
                <th key={stat} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {stat}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {availableUsageTypes.map(usageType => {
              const data = usage_breakdown[usageType];
              const stats = statConfig.type === 'pitching' ? data.stats.pitching : data.stats.batting;
              
              if (!data || data.days === 0) return null;

              const isOtherRoster = usageType === 'other_roster';
              const hasMultipleTeams = isOtherRoster && data.teams && data.teams.length > 1;
              const isExpanded = expandedRows.has(usageType);

              const rows = [];
              
              // Main row
              rows.push(
                <tr key={usageType} className={isOtherRoster && hasMultipleTeams ? 'cursor-pointer hover:bg-gray-50' : ''}>
                  <td className="px-6 py-4 whitespace-nowrap" onClick={hasMultipleTeams ? () => toggleRowExpansion(usageType) : undefined}>
                    <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getUsageColor(usageType)}`}>
                      {hasMultipleTeams && (
                        <svg className={`w-3 h-3 mr-1 transition-transform ${isExpanded ? 'rotate-90' : ''}`} fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                      {getUsageTitle(usageType)}
                      {hasMultipleTeams && (
                        <span className="ml-1 text-xs opacity-75">({data.teams.length} teams)</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className="font-medium">{data.days}</span>
                  </td>
                  {statConfig.stats.map(stat => (
                    <td key={stat} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {stats ? formatStatValue(stat, stats[stat]) : '-'}
                    </td>
                  ))}
                </tr>
              );

              // Expanded team rows for other_roster
              if (isOtherRoster && hasMultipleTeams && isExpanded) {
                data.teams.forEach((team, index) => {
                  const teamStats = statConfig.type === 'pitching' ? team.stats.pitching : team.stats.batting;
                  rows.push(
                    <tr key={`${usageType}-team-${index}`} className="bg-purple-25">
                      <td className="px-6 py-4 whitespace-nowrap pl-12">
                        <div className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-purple-600 bg-purple-100">
                          {team.team_name}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {team.from_date} to {team.to_date}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                        <span className="font-medium">{team.days}</span>
                      </td>
                      {statConfig.stats.map(stat => (
                        <td key={stat} className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                          {teamStats ? formatStatValue(stat, teamStats[stat]) : '-'}
                        </td>
                      ))}
                    </tr>
                  );
                });
              }

              return rows;
            }).flat()}
          </tbody>
        </table>
      </div>

      {/* Statistical Notes */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-800 mb-1">
              Statistical Notes
            </h4>
            <div className="text-sm text-blue-700">
              {statConfig.type === 'pitching' ? (
                <ul className="list-disc list-inside space-y-1">
                  <li>APP = Pitching Appearances, W = Wins, SV = Saves, K = Strikeouts, HLD = Holds</li>
                  <li>ERA = (Earned Runs × 9) ÷ Innings Pitched</li>
                  <li>WHIP = (Walks + Hits) ÷ Innings Pitched</li>
                  <li>K/BB = Strikeouts ÷ Walks, QS = Quality Starts</li>
                </ul>
              ) : (
                <ul className="list-disc list-inside space-y-1">
                  <li>R = Runs, H = Hits, 3B = Triples, HR = Home Runs, RBI = Runs Batted In, SB = Stolen Bases</li>
                  <li>AVG = Hits ÷ At Bats</li>
                  <li>OBP = (Hits + Walks + Hit by Pitch) ÷ (At Bats + Walks + Hit by Pitch + Sacrifice Flies)</li>
                  <li>SLG = Total Bases ÷ At Bats</li>
                </ul>
              )}
              <p className="mt-2">Statistics are aggregated across all games in each roster status category.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceBreakdown;