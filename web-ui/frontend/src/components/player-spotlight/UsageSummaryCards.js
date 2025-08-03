import React from 'react';

const UsageSummaryCards = ({ usageBreakdown, season }) => {
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
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
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
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
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
      )
    },
    {
      key: 'not_owned',
      title: 'Not Owned',
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
          Season Usage Summary with Performance
        </h2>
        <p className="text-gray-600">
          Analysis of {total_days} total days in {season} season
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
        {usageTypes.map(type => {
          const data = breakdown[type.key] || { days: 0, percentage: 0, positions: [] };
          const percentage = data.percentage || 0;
          const days = data.days || 0;

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
                
                {/* Position breakdown */}
                {data.positions && data.positions.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Positions:</p>
                    <div className="flex flex-wrap gap-1">
                      {data.positions.slice(0, 3).map((pos, index) => (
                        <span 
                          key={index}
                          className="px-2 py-1 bg-white bg-opacity-60 text-xs rounded font-medium"
                        >
                          {pos}
                        </span>
                      ))}
                      {data.positions.length > 3 && (
                        <span className="px-2 py-1 bg-white bg-opacity-60 text-xs rounded font-medium">
                          +{data.positions.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Performance statistics placeholder */}
                {type.key === 'started' && days > 0 && (
                  <div className="mt-3 pt-3 border-t border-green-200">
                    <p className="text-xs text-green-600 font-medium">
                      Performance stats available in future update
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary insight */}
      {total_days > 0 && (
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                {breakdown.started.percentage > 60 
                  ? "High usage player with strong starting percentage" 
                  : breakdown.started.percentage > 40 
                    ? "Moderate usage player with decent starting opportunities"
                    : "Limited usage player or frequently on other rosters"
                }
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsageSummaryCards;