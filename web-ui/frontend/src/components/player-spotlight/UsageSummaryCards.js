import React from 'react';

const UsageSummaryCards = ({ usageBreakdown, monthlyData, season }) => {
  // Helper function to calculate IL insights
  const calculateILInsights = (ilData, totalDays) => {
    if (!ilData || ilData.days === 0) return null;
    
    // Calculate IL months from monthly data
    let ilMonths = 0;
    if (monthlyData && monthlyData.length > 0) {
      ilMonths = monthlyData.filter(month => 
        month.summary && month.summary.injured_list > 0
      ).length;
    }
    
    // Fantasy impact analysis
    const percentage = ilData.percentage || 0;
    let riskLevel = 'Low';
    let riskColor = 'text-green-600';
    if (percentage > 30) {
      riskLevel = 'High';
      riskColor = 'text-red-600';
    } else if (percentage > 15) {
      riskLevel = 'Moderate';
      riskColor = 'text-yellow-600';
    }
    
    return {
      ilMonths,
      riskLevel,
      riskColor
    };
  };

  // Color schemes for each usage type
  const usageTypes = [
    {
      key: 'started',
      title: 'Started',
      color: 'green',
      bgColor: 'bg-green-50',
      textColor: 'text-green-700',
      accentColor: 'text-green-600',
      borderColor: 'border-green-200',
      icon: (
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      )
    },
    {
      key: 'benched',
      title: 'Benched',
      color: 'orange',
      bgColor: 'bg-orange-50',
      textColor: 'text-orange-700',
      accentColor: 'text-orange-600',
      borderColor: 'border-orange-200',
      icon: (
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M4 18v-2h16v2H4zm2-4V8c0-1.1.9-2 2-2h8c1.1 0 2 .9 2 2v6h-2V8H8v6H6zm-2 0V8c0-2.21 1.79-4 4-4h8c2.21 0 4 1.79 4 4v6h2v2H2v-2h2z"/>
        </svg>
      )
    },
    {
      key: 'injured_list',
      title: 'Injured List',
      color: 'red',
      bgColor: 'bg-red-50',
      textColor: 'text-red-700',
      accentColor: 'text-red-600',
      borderColor: 'border-red-200',
      icon: (
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M19,3H5C3.9,3 3,3.9 3,5V19C3,20.1 3.9,21 5,21H19C20.1,21 21,20.1 21,19V5C21,3.9 20.1,3 19,3M18,14H13V19H11V14H6V12H11V7H13V12H18V14Z"/>
        </svg>
      )
    },
    {
      key: 'other_roster',
      title: 'On Another Roster',
      color: 'purple',
      bgColor: 'bg-purple-50',
      textColor: 'text-purple-700',
      accentColor: 'text-purple-600',
      borderColor: 'border-purple-200',
      icon: (
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 20 20">
          <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
        </svg>
      ),
      showTeams: true  // Flag to show team breakdown
    },
    {
      key: 'not_rostered',
      title: 'Not Rostered',
      color: 'gray',
      bgColor: 'bg-gray-50',
      textColor: 'text-gray-700',
      accentColor: 'text-gray-600',
      borderColor: 'border-gray-200',
      icon: (
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      )
    },
    {
      key: 'minor_leagues',
      title: 'Minor Leagues',
      color: 'yellow',
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-700',
      accentColor: 'text-yellow-600',
      borderColor: 'border-yellow-200',
      icon: (
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10.394 2.08a1 1 0 00-.788 0l-7 3a1 1 0 000 1.84L5.25 8.051a.999.999 0 01.356-.257l4-1.714a1 1 0 11.788 1.838L7.667 9.088l1.94.831a1 1 0 00.787 0l7-3a1 1 0 000-1.838l-7-3zM3.31 9.397L5 10.12v4.102a8.969 8.969 0 00-1.05-.174 1 1 0 01-.89-.89 11.115 11.115 0 01.25-3.762zM9.3 16.573A9.026 9.026 0 007 14.935v-3.957l1.818.78a3 3 0 002.364 0l5.508-2.361a11.026 11.026 0 01.25 3.762 1 1 0 01-.89.89 8.968 8.968 0 00-5.35 2.524 1 1 0 01-1.4 0zM6 18a1 1 0 001-1v-2.065a8.935 8.935 0 00-2-.712V17a1 1 0 001 1z" />
        </svg>
      )
    }
  ];

  if (!usageBreakdown || !usageBreakdown.usage_breakdown) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
        {usageTypes.map(type => (
          <div key={type.key} className={`${type.bgColor} ${type.borderColor} border rounded-lg p-6`}>
            <div className="flex items-center">
              <div className={`${type.accentColor} mr-3`}>
                {type.icon}
              </div>
              <div>
                <h3 className={`text-lg font-semibold ${type.textColor}`}>{type.title}</h3>
                <p className="text-2xl font-bold text-gray-900">0%</p>
                <p className="text-sm text-gray-600">0 of 0 total days</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  const { usage_breakdown: breakdown, total_days } = usageBreakdown;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Usage Summary
        </h2>
        <p className="text-gray-600">
          Analysis of {total_days} total days in {season} season
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
        {usageTypes.map(type => {
          const data = breakdown[type.key] || { days: 0, percentage: 0, positions: [] };
          // Handle backward compatibility for old 'not_owned' key
          const actualData = type.key === 'not_rostered' && !data.days && breakdown.not_owned ? 
            breakdown.not_owned : data;
          const days = actualData.days || 0;
          // Calculate percentage if not provided (for performance breakdown API compatibility)
          const percentage = actualData.percentage || (total_days > 0 ? (days / total_days) * 100 : 0);
          
          // Calculate IL insights for injured list cards
          const ilInsights = type.key === 'injured_list' ? calculateILInsights(actualData, total_days) : null;

          return (
            <div 
              key={type.key} 
              className={`${type.bgColor} ${type.borderColor} border rounded-lg p-6 hover:shadow-md transition-shadow`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className={`${type.accentColor} mr-3`}>
                  {type.icon}
                </div>
                <div className="text-right">
                  <p className={`text-3xl font-bold ${type.accentColor}`}>
                    {percentage.toFixed(0)}%
                  </p>
                </div>
              </div>
              
              <div>
                <h3 className={`text-lg font-semibold ${type.textColor} mb-1`}>
                  {type.title}
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  {days} of {total_days} total days
                </p>
                
                {/* Team breakdown for Other Roster */}
                {type.showTeams && actualData.teams && actualData.teams.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Teams:</p>
                    <div className="space-y-1">
                      {actualData.teams.map((team, index) => {
                        // Handle both string and object formats for backward compatibility
                        const teamName = typeof team === 'string' ? team : team.name;
                        const teamDays = typeof team === 'object' ? team.days : 0;
                        const teamPercentage = typeof team === 'object' && team.percentage !== undefined ? team.percentage : 0;
                        
                        return (
                          <div 
                            key={index} 
                            className="bg-white bg-opacity-60 rounded px-2 py-1 cursor-help relative group"
                            title={`${teamName}: ${teamDays} days (${teamPercentage.toFixed(1)}% of season)`}
                          >
                            <div className="text-xs font-medium text-purple-700 truncate">
                              {teamName}
                            </div>
                            <div className="text-xs text-purple-600">
                              {teamDays} days ({teamPercentage.toFixed(0)}%)
                            </div>
                            
                            {/* Enhanced tooltip on hover */}
                            <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block z-10">
                              <div className="bg-gray-900 text-white text-xs rounded py-2 px-3 whitespace-nowrap">
                                <div className="font-semibold">{teamName}</div>
                                <div>{teamDays} days ({teamPercentage.toFixed(1)}% of season)</div>
                                <div className="mt-1 text-gray-300">
                                  {teamDays > 0 ? ((teamDays / total_days) * 100).toFixed(1) : 0}% of total tracked days
                                </div>
                                <div className="absolute top-full left-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Position breakdown for non-team cards (exclude Minor Leagues, Injured List, and Not Rostered) */}
                {!type.showTeams && type.key !== 'minor_leagues' && type.key !== 'injured_list' && type.key !== 'not_rostered' && actualData.positions && actualData.positions.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Positions:</p>
                    <div className="flex flex-wrap gap-1">
                      {actualData.positions.slice(0, 3).map((pos, index) => (
                        <span 
                          key={index}
                          className="px-2 py-1 bg-white bg-opacity-60 text-xs rounded font-medium"
                        >
                          {pos}
                        </span>
                      ))}
                      {actualData.positions.length > 3 && (
                        <span className="px-2 py-1 bg-white bg-opacity-60 text-xs rounded font-medium">
                          +{actualData.positions.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* IL-specific insights */}
                {type.key === 'injured_list' && ilInsights && days > 0 && (
                  <div className="mt-3 pt-3 border-t border-red-200">
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">IL Months:</span>
                        <span className="text-xs font-medium text-red-700">{ilInsights.ilMonths}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Risk Level:</span>
                        <span className={`text-xs font-medium ${ilInsights.riskColor}`}>{ilInsights.riskLevel}</span>
                      </div>
                    </div>
                  </div>
                )}

              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default UsageSummaryCards;