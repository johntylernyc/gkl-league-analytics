import React, { useState, useMemo } from 'react';

const MonthlyTimeline = ({ monthlyData, season, playerName }) => {
  const [hoveredMonth, setHoveredMonth] = useState(null);
  const [selectedTeam, setSelectedTeam] = useState(null);

  // Get the current team (most recent team) - moved before teamColors
  const currentTeam = useMemo(() => {
    if (!monthlyData || monthlyData.length === 0) return null;
    const lastMonth = monthlyData[monthlyData.length - 1];
    if (lastMonth.teams && lastMonth.teams.length > 0) {
      // Find the team with the most recent activity
      return lastMonth.teams[lastMonth.teams.length - 1].team_name;
    }
    return null;
  }, [monthlyData]);

  // Extract all unique teams from the data and assign colors
  const teamColors = useMemo(() => {
    const teams = new Set();
    monthlyData?.forEach(month => {
      if (month.teams) {
        month.teams.forEach(team => teams.add(team.team_name));
      }
    });
    
    // Color palettes for non-current teams only
    const colorPalettes = [
      { bg: 'bg-blue-500', border: 'border-blue-600', text: 'text-blue-700', light: 'bg-blue-100' },
      { bg: 'bg-purple-500', border: 'border-purple-600', text: 'text-purple-700', light: 'bg-purple-100' },
      { bg: 'bg-indigo-500', border: 'border-indigo-600', text: 'text-indigo-700', light: 'bg-indigo-100' },
      { bg: 'bg-pink-500', border: 'border-pink-600', text: 'text-pink-700', light: 'bg-pink-100' },
      { bg: 'bg-teal-500', border: 'border-teal-600', text: 'text-teal-700', light: 'bg-teal-100' },
    ];
    
    const teamMap = {};
    let colorIndex = 0;
    Array.from(teams).forEach((team) => {
      // Current team will always use green, so don't assign a special color
      if (team !== currentTeam) {
        teamMap[team] = colorPalettes[colorIndex % colorPalettes.length];
        colorIndex++;
      }
    });
    
    return teamMap;
  }, [monthlyData, currentTeam]);

  // Color mapping for different status types with team awareness
  const getStatusColor = (status, team) => {
    const isCurrentTeam = team === currentTeam;
    const teamColor = teamColors[team];
    
    // For current team, always use standard colors
    if (isCurrentTeam) {
      if (['BN'].includes(status)) return 'bg-orange-400';
      if (['IL', 'IL10', 'IL15', 'IL60'].includes(status)) return 'bg-red-400';
      if (status === 'NA') return 'bg-yellow-400'; // Minor leagues
      if (status === 'Not Owned' || status === 'FA' || status === 'Not Rostered') return 'bg-gray-400';
      return 'bg-green-400'; // Started positions
    }
    
    // For other teams, use their team color
    if (teamColor) {
      // Use the team's color for all their activities (started/benched)
      // But keep IL as red, NA as yellow, and Not Owned as gray
      if (['IL', 'IL10', 'IL15', 'IL60'].includes(status)) return 'bg-red-400';
      if (status === 'NA') return 'bg-yellow-400'; // Minor leagues
      if (status === 'Not Owned' || status === 'FA' || status === 'Not Rostered') return 'bg-gray-400';
      return teamColor.bg; // Use team color for both started and benched
    }
    
    // Fallback colors if no team color assigned
    return 'bg-gray-300';
  };

  const getStatusLabel = (status) => {
    if (['BN'].includes(status)) return 'Benched';
    if (['IL', 'IL10', 'IL15', 'IL60'].includes(status)) return 'Injured List';
    if (status === 'NA') return 'Minor Leagues';
    if (status === 'Not Owned' || status === 'FA' || status === 'Not Rostered') return 'Not Rostered';
    return 'Started';
  };

  // Generate timeline bars for each month with team segments
  const generateTimelineBar = (monthData) => {
    const totalDays = monthData.total_days;
    const segments = [];
    let accountedDays = 0;

    // Calculate total days accounted for in the data
    if (monthData.teams && monthData.teams.length > 0) {
      accountedDays = monthData.teams.reduce((sum, team) => sum + team.days, 0);
    } else if (monthData.positions && monthData.positions.length > 0) {
      accountedDays = monthData.positions.reduce((sum, pos) => sum + pos.days, 0);
    }

    // If we have team data, organize by team
    if (monthData.teams && monthData.teams.length > 0) {
      // Sort teams chronologically by the earliest position start date
      const sortedTeams = [...monthData.teams].sort((a, b) => {
        const aEarliest = a.positions.reduce((earliest, pos) => 
          !earliest || (pos.period_start && pos.period_start < earliest) ? pos.period_start : earliest, null);
        const bEarliest = b.positions.reduce((earliest, pos) => 
          !earliest || (pos.period_start && pos.period_start < earliest) ? pos.period_start : earliest, null);
        return (aEarliest || '').localeCompare(bEarliest || '');
      });

      sortedTeams.forEach((teamData, teamIndex) => {
        const teamPercentage = (teamData.days / totalDays) * 100;
        const isCurrentTeam = teamData.team_name === currentTeam;
        const teamColor = teamColors[teamData.team_name];
        
        // Create segments for this team's positions
        const teamSegments = [];
        let runningPercentage = 0;
        
        // Sort positions chronologically within this team
        const sortedPositions = [...teamData.positions].sort((a, b) => 
          (a.period_start || '').localeCompare(b.period_start || ''));
        
        sortedPositions.forEach((pos, posIndex) => {
          const posPercentage = (pos.days / teamData.days) * teamPercentage;
          const color = getStatusColor(pos.position, teamData.team_name);
          
          teamSegments.push(
            <div
              key={`${teamIndex}-${posIndex}`}
              className={`${color} h-full flex items-center justify-center relative transition-opacity hover:opacity-100`}
              style={{ 
                width: `${posPercentage}%`,
                opacity: selectedTeam && selectedTeam !== teamData.team_name ? 0.3 : 1
              }}
              title={`${teamData.team_name} - ${pos.position}: ${pos.days} days${pos.period_start && pos.period_end ? ` (${pos.period_start} to ${pos.period_end})` : ''}`}
            >
              {posPercentage > 10 && (
                <span className="text-xs font-medium text-white">
                  {pos.days}
                </span>
              )}
            </div>
          );
          runningPercentage += posPercentage;
        });
        
        // Add team separator if not the last team
        if (teamIndex < monthData.teams.length - 1) {
          teamSegments.push(
            <div key={`separator-${teamIndex}`} className="w-px h-full bg-gray-600"></div>
          );
        }
        
        segments.push(...teamSegments);
      });
    } else if (monthData.positions && monthData.positions.length > 0) {
      // Fallback to position-only display
      const sortedPositions = [...monthData.positions].sort((a, b) => 
        (a.period_start || '').localeCompare(b.period_start || ''));
      
      sortedPositions.forEach((pos, index) => {
        const percentage = (pos.days / totalDays) * 100;
        const color = getStatusColor(pos.position, currentTeam);
        
        segments.push(
          <div
            key={index}
            className={`${color} h-full flex items-center justify-center relative`}
            style={{ width: `${percentage}%` }}
            title={`${pos.position}: ${pos.days} days${pos.period_start && pos.period_end ? ` (${pos.period_start} to ${pos.period_end})` : ''}`}
          >
            {percentage > 15 && (
              <span className="text-xs font-medium text-white">
                {pos.days}
              </span>
            )}
          </div>
        );
      });
    }

    // Calculate unaccounted days (excluding future days)
    const futureDays = monthData.future_days || 0;
    const notRosteredDays = totalDays - accountedDays - futureDays;
    
    // Create an array to collect all segments with chronological information
    const allSegments = [...segments];
    
    // Add "Not Rostered" segment if there are unaccounted days
    // Note: These should be distributed chronologically, but without date info
    // we place them at the beginning as they typically represent pre-ownership periods
    if (notRosteredDays > 0) {
      const notRosteredPercentage = (notRosteredDays / totalDays) * 100;
      const notRosteredSegment = (
        <div
          key="not-rostered"
          className="bg-gray-400 h-full flex items-center justify-center relative"
          style={{ width: `${notRosteredPercentage}%` }}
          title={`Not Rostered: ${notRosteredDays} days`}
        >
          {notRosteredPercentage > 8 && (
            <span className="text-xs font-medium text-white">
              {notRosteredDays}
            </span>
          )}
        </div>
      );
      
      // Place not rostered segment at the beginning for months where player wasn't owned initially
      allSegments.unshift(notRosteredSegment);
    }

    // Add transparent segment for future days at the end (days that haven't happened yet)
    if (futureDays > 0) {
      const futureDaysPercentage = (futureDays / totalDays) * 100;
      allSegments.push(
        <div
          key="future-days"
          className="bg-transparent h-full flex items-center justify-center relative border border-gray-300"
          style={{ 
            width: `${futureDaysPercentage}%`,
            backgroundColor: 'transparent'
          }}
          title={`Future days: ${futureDays} days`}
        >
          {/* No text for future days */}
        </div>
      );
    }

    // Handle case where there's no data at all
    if (allSegments.length === 0) {
      return (
        <div className="h-8 bg-gray-400 rounded flex items-center justify-center">
          <span className="text-xs font-medium text-white">Not Rostered ({totalDays} days)</span>
        </div>
      );
    }

    return (
      <div className="h-8 bg-gray-200 rounded flex overflow-hidden border border-gray-300">
        {allSegments}
      </div>
    );
  };

  const formatMonthYear = (monthData) => {
    // Handle month_year format like "2025-07"
    if (monthData.month_year) {
      const [year, month] = monthData.month_year.split('-');
      const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                         'July', 'August', 'September', 'October', 'November', 'December'];
      return `${monthNames[parseInt(month) - 1]} ${year}`;
    }
    // Fallback to original format
    return `${monthData.month} ${monthData.year}`;
  };

  if (!monthlyData || monthlyData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Monthly Timeline
        </h2>
        <div className="text-center py-8">
          <div className="text-gray-400 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="text-gray-600">No timeline data available for {season} season</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Monthly Timeline
        </h2>
        <p className="text-gray-600">
          {playerName}'s usage patterns throughout {season} season
        </p>
      </div>

      {/* Team Legend */}
      {(Object.keys(teamColors).length > 0 || currentTeam) && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 mb-2">Team Ownership:</div>
          <div className="flex flex-wrap gap-3">
            {/* Show previous teams with their colors */}
            {Object.entries(teamColors).map(([team, colors]) => (
              <button
                key={team}
                onClick={() => setSelectedTeam(selectedTeam === team ? null : team)}
                className={`flex items-center px-3 py-1 rounded-full text-sm font-medium transition-all ${
                  selectedTeam === team 
                    ? `${colors.light} ${colors.text} ring-2 ring-offset-1 ${colors.border}` 
                    : selectedTeam && selectedTeam !== team
                      ? 'bg-gray-100 text-gray-400'
                      : `${colors.light} ${colors.text} hover:ring-2 hover:ring-offset-1 ${colors.border}`
                }`}
              >
                <div className={`w-3 h-3 ${colors.bg} rounded-full mr-2`}></div>
                <span>{team}</span>
              </button>
            ))}
            {/* Show current team with green color */}
            {currentTeam && (
              <button
                onClick={() => setSelectedTeam(selectedTeam === currentTeam ? null : currentTeam)}
                className={`flex items-center px-3 py-1 rounded-full text-sm font-medium transition-all ${
                  selectedTeam === currentTeam 
                    ? 'bg-green-100 text-green-700 ring-2 ring-offset-1 border-green-600' 
                    : selectedTeam && selectedTeam !== currentTeam
                      ? 'bg-gray-100 text-gray-400'
                      : 'bg-green-100 text-green-700 hover:ring-2 hover:ring-offset-1 border-green-600'
                }`}
              >
                <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                <span>{currentTeam}</span>
                <span className="ml-2 text-xs opacity-75">(Current)</span>
              </button>
            )}
            {selectedTeam && (
              <button
                onClick={() => setSelectedTeam(null)}
                className="text-sm text-gray-600 hover:text-gray-900 px-2"
              >
                Clear filter
              </button>
            )}
          </div>
        </div>
      )}

      {/* Status Legend */}
      <div className="mb-6 flex flex-wrap gap-4 text-sm">
        <div className="flex items-center">
          <div className="w-4 h-4 bg-green-400 rounded mr-2"></div>
          <span>Started</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-orange-400 rounded mr-2"></div>
          <span>Benched</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-red-400 rounded mr-2"></div>
          <span>Injured List</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-yellow-400 rounded mr-2"></div>
          <span>Minor Leagues</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-gray-400 rounded mr-2"></div>
          <span>Not Rostered</span>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-4">
        {monthlyData.map((monthData, index) => {
          // Calculate team-specific summaries
          const teamSummaries = {};
          if (monthData.teams) {
            monthData.teams.forEach(team => {
              teamSummaries[team.team_name] = {
                days: team.days,
                started: team.summary?.started || 0,
                benched: team.summary?.benched || 0
              };
            });
          }
          
          return (
            <div 
              key={index}
              className="relative"
              onMouseEnter={() => setHoveredMonth(index)}
              onMouseLeave={() => setHoveredMonth(null)}
            >
              {/* Month Header */}
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-900">
                  {formatMonthYear(monthData)}
                </h3>
                <div className="text-right text-sm text-gray-600">
                  {Object.keys(teamSummaries).length > 0 ? (
                    <div className="flex gap-3">
                      {Object.entries(teamSummaries).map(([team, summary]) => (
                        <span key={team} className="inline-flex items-center">
                          <span className={`w-2 h-2 rounded-full mr-1 ${teamColors[team]?.bg || 'bg-gray-400'}`}></span>
                          <span>{summary.started}/{summary.benched}</span>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <>
                      <span>{monthData.summary.started} started</span>
                      <span className="mx-1">/</span>
                      <span>{monthData.summary.benched} benched</span>
                      {monthData.summary.injured_list > 0 && (
                        <>
                          <span className="mx-1">/</span>
                          <span>{monthData.summary.injured_list} IL</span>
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Timeline Bar */}
              <div className="relative">
                {generateTimelineBar(monthData)}
                
                {/* Hover Tooltip */}
                {hoveredMonth === index && (
                  <div className="absolute z-10 left-0 top-10 bg-black bg-opacity-90 text-white text-xs rounded-lg p-3 shadow-lg" style={{ minWidth: '200px' }}>
                    <div className="font-medium mb-2 text-sm">{formatMonthYear(monthData)}</div>
                    
                    {monthData.teams && monthData.teams.length > 0 ? (
                      <>
                        {monthData.teams.map((team, teamIdx) => (
                          <div key={teamIdx} className="mb-2">
                            <div className="font-medium text-yellow-300 mb-1">
                              {team.team_name} ({team.days} days)
                            </div>
                            {team.positions.map((pos, posIdx) => (
                              <div key={posIdx} className="pl-3">
                                <div className="flex justify-between">
                                  <span>{pos.position}:</span>
                                  <span>{pos.days} days</span>
                                </div>
                                {pos.period_start && pos.period_end && (
                                  <div className="text-xs text-gray-300 pl-2">
                                    {pos.period_start} to {pos.period_end}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        ))}
                      </>
                    ) : (
                      <>
                        {monthData.positions.map((pos, posIndex) => (
                          <div key={posIndex}>
                            <div className="flex justify-between">
                              <span className="mr-3">{pos.position}:</span>
                              <span>{pos.days} days</span>
                            </div>
                            {pos.period_start && pos.period_end && (
                              <div className="text-xs text-gray-300 pl-2">
                                {pos.period_start} to {pos.period_end}
                              </div>
                            )}
                          </div>
                        ))}
                      </>
                    )}
                    
                    <div className="border-t border-gray-400 mt-2 pt-2">
                      <div className="flex justify-between font-medium">
                        <span>Total:</span>
                        <span>{monthData.total_days} days</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Data availability notice */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-blue-700">
              Timeline shows data through {monthlyData[monthlyData.length - 1]?.latest_date || 'current date'}. 
              Future dates will become available as the season progresses.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MonthlyTimeline;