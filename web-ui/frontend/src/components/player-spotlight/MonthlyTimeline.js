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


  // Generate timeline bars for each month with day-by-day chronological representation
  const generateTimelineBar = (monthData) => {
    const [year, month] = monthData.month_year.split('-');
    const monthStartDate = new Date(parseInt(year), parseInt(month) - 1, 1);
    const monthEndDate = new Date(parseInt(year), parseInt(month), 0); // Last day of month
    const totalDaysInMonth = monthEndDate.getDate();
    
    // Define actual season start dates by year
    const seasonStartDates = {
      2025: new Date('2025-03-27'),
      2024: new Date('2024-03-28'),
      2023: new Date('2023-03-30'),
      2022: new Date('2022-04-07'),
      2021: new Date('2021-04-01'),
      2020: new Date('2020-07-23'),
      2019: new Date('2019-03-28'),
      2018: new Date('2018-03-29'),
      2017: new Date('2017-04-02'),
      2016: new Date('2016-04-03'),
      2015: new Date('2015-04-05'),
      2014: new Date('2014-03-30'),
      2013: new Date('2013-03-31'),
      2012: new Date('2012-03-28'),
      2011: new Date('2011-03-31'),
      2010: new Date('2010-04-04'),
      2009: new Date('2009-04-05'),
      2008: new Date('2008-03-25')
    };
    
    const seasonStartDate = seasonStartDates[parseInt(year)] || new Date(parseInt(year), 3, 1); // Fallback to April 1st
    const currentDate = new Date();
    
    // Create a day-by-day status map
    const dayStatusMap = {};
    
    // First, mark all days as their default status
    for (let day = 1; day <= totalDaysInMonth; day++) {
      const dateStr = `${year}-${month.padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
      const dayDate = new Date(parseInt(year), parseInt(month) - 1, day);
      
      if (dayDate < seasonStartDate) {
        dayStatusMap[dateStr] = { status: 'pre-season', team: null };
      } else if (dayDate > currentDate) {
        dayStatusMap[dateStr] = { status: 'future', team: null };
      } else {
        dayStatusMap[dateStr] = { status: 'not-rostered', team: null };
      }
    }
    
    // Then, fill in actual roster data
    if (monthData.teams && monthData.teams.length > 0) {
      // Find the latest roster period in this month to handle month-end boundary
      let latestPeriod = null;
      let latestEndDate = null;
      
      monthData.teams.forEach(teamData => {
        teamData.positions.forEach(pos => {
          if (pos.period_start && pos.period_end) {
            const startDate = new Date(pos.period_start);
            const endDate = new Date(pos.period_end);
            
            // Fill each day in this period (use safer date iteration)
            const startDateStr = pos.period_start;
            const endDateStr = pos.period_end;
            const start = new Date(startDateStr);
            const end = new Date(endDateStr);
            
            for (let current = new Date(start); current <= end; current.setUTCDate(current.getUTCDate() + 1)) {
              const dateStr = current.toISOString().split('T')[0];
              if (dayStatusMap[dateStr]) {
                dayStatusMap[dateStr] = {
                  status: pos.position,
                  team: teamData.team_name
                };
              }
            }
            
            // Track the latest period for month-end extension
            if (!latestEndDate || endDate > latestEndDate) {
              latestEndDate = endDate;
              latestPeriod = {
                position: pos.position,
                team: teamData.team_name,
                endDate: endDate
              };
            }
          }
        });
      });
      
      // Extend the latest period to cover remaining days in month (if not future dates)
      if (latestPeriod && latestEndDate) {
        // Check if the latest period ends before the last day of the current month
        const latestEndDay = latestEndDate.getDate();
        const latestEndMonth = latestEndDate.getMonth();
        const latestEndYear = latestEndDate.getFullYear();
        
        // Only extend if the latest period ends within the current month but before the last day
        if (latestEndYear === parseInt(year) && 
            latestEndMonth === parseInt(month) - 1 && 
            latestEndDay < totalDaysInMonth) {
          
          // Fill remaining days in month with the latest period's status
          for (let day = latestEndDay + 1; day <= totalDaysInMonth; day++) {
            const dateStr = `${year}-${month.padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
            
            // Only extend if currently marked as not-rostered (skip future date check for now to debug)
            if (dayStatusMap[dateStr] && dayStatusMap[dateStr].status === 'not-rostered') {
              dayStatusMap[dateStr] = {
                status: latestPeriod.position,
                team: latestPeriod.team
              };
            }
          }
        }
      }
    } else if (monthData.positions && monthData.positions.length > 0) {
      // Fallback to position-only data
      monthData.positions.forEach(pos => {
        if (pos.period_start && pos.period_end) {
          const startDate = new Date(pos.period_start);
          const endDate = new Date(pos.period_end);
          
          for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
            const dateStr = d.toISOString().split('T')[0];
            if (dayStatusMap[dateStr]) {
              dayStatusMap[dateStr] = {
                status: pos.position,
                team: currentTeam
              };
            }
          }
        }
      });
    }
    
    // Group consecutive days with same status for rendering
    const segments = [];
    let currentSegment = null;
    
    for (let day = 1; day <= totalDaysInMonth; day++) {
      const dateStr = `${year}-${month.padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
      const dayData = dayStatusMap[dateStr];
      
      if (!currentSegment || 
          currentSegment.status !== dayData.status || 
          currentSegment.team !== dayData.team) {
        // Start new segment
        if (currentSegment) {
          segments.push(currentSegment);
        }
        currentSegment = {
          status: dayData.status,
          team: dayData.team,
          days: 1,
          startDay: day,
          endDay: day
        };
      } else {
        // Continue current segment
        currentSegment.days++;
        currentSegment.endDay = day;
      }
    }
    
    // Don't forget the last segment
    if (currentSegment) {
      segments.push(currentSegment);
    }
    
    // Render segments
    const renderedSegments = segments.map((segment, index) => {
      const percentage = (segment.days / totalDaysInMonth) * 100;
      let className, title;
      
      switch (segment.status) {
        case 'pre-season':
          return (
            <div
              key={`segment-${index}`}
              className="bg-transparent h-full"
              style={{ width: `${percentage}%` }}
              title={`Pre-season: ${segment.days} days`}
            />
          );
        case 'future':
          return (
            <div
              key={`segment-${index}`}
              className="bg-white bg-opacity-50 h-full"
              style={{ width: `${percentage}%` }}
              title={`Future: ${segment.days} days`}
            />
          );
        case 'not-rostered':
          className = 'bg-gray-400 h-full flex items-center justify-center relative';
          title = `Not Rostered: ${segment.days} days`;
          break;
        default:
          const color = getStatusColor(segment.status, segment.team);
          className = `${color} h-full flex items-center justify-center relative transition-opacity hover:opacity-100`;
          title = `${segment.team || 'Unknown'} - ${segment.status}: ${segment.days} days`;
          break;
      }
      
      return (
        <div
          key={`segment-${index}`}
          className={className}
          style={{ 
            width: `${percentage}%`,
            opacity: selectedTeam && segment.team && selectedTeam !== segment.team ? 0.3 : 1
          }}
          title={title}
        >
        </div>
      );
    });

    return (
      <div className="h-8 bg-gray-200 rounded flex overflow-hidden border border-gray-300">
        {renderedSegments}
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
          return (
            <div 
              key={index}
              className="relative"
              onMouseEnter={() => setHoveredMonth(index)}
              onMouseLeave={() => setHoveredMonth(null)}
            >
              {/* Month Header */}
              <div className="mb-2">
                <h3 className="text-sm font-medium text-gray-900">
                  {formatMonthYear(monthData)}
                </h3>
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
                    
                    {/* Show Not Rostered days if any */}
                    {monthData.summary && monthData.summary.not_rostered > 0 && (
                      <div className="mt-2">
                        <div className="flex justify-between">
                          <span className="mr-3">Not Rostered:</span>
                          <span>{monthData.summary.not_rostered} days</span>
                        </div>
                      </div>
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