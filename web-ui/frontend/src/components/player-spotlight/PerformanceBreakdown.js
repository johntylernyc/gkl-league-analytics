import React, { useState } from 'react';

const PerformanceBreakdown = ({ usageBreakdown, playerName, season }) => {
  const [activeTab, setActiveTab] = useState('overview');

  // Mock performance statistics - in a real implementation, this would come from the API
  const generateMockStats = (usageType, days) => {
    if (days === 0) return null;
    
    // Generate realistic-looking mock stats based on usage type
    const baseStats = {
      started: { R: 45, H: 68, HR: 12, RBI: 38, SB: 8, AVG: 0.284, OBP: 0.356, SLG: 0.487 },
      benched: { R: 8, H: 12, HR: 2, RBI: 7, SB: 1, AVG: 0.240, OBP: 0.298, SLG: 0.380 },
      other_roster: { R: 0, H: 0, HR: 0, RBI: 0, SB: 0, AVG: 0.000, OBP: 0.000, SLG: 0.000 },
      not_owned: { R: 0, H: 0, HR: 0, RBI: 0, SB: 0, AVG: 0.000, OBP: 0.000, SLG: 0.000 }
    };

    return baseStats[usageType] || null;
  };

  const formatStatValue = (stat, value) => {
    if (['AVG', 'OBP', 'SLG'].includes(stat)) {
      return value.toFixed(3);
    }
    return value.toString();
  };

  const getUsageColor = (usageType) => {
    switch (usageType) {
      case 'started': return 'text-green-600 bg-green-50 border-green-200';
      case 'benched': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'injured_list': return 'text-red-600 bg-red-50 border-red-200';
      case 'other_roster': return 'text-purple-600 bg-purple-50 border-purple-200';
      case 'not_owned': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getUsageTitle = (usageType) => {
    switch (usageType) {
      case 'started': return 'Started';
      case 'benched': return 'Benched';
      case 'injured_list': return 'Injured List';
      case 'other_roster': return 'On Another Roster';
      case 'not_owned': return 'Not Owned';
      default: return usageType;
    }
  };

  if (!usageBreakdown || !usageBreakdown.usage_breakdown) {
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
          <p className="text-gray-600">No performance data available</p>
        </div>
      </div>
    );
  }

  const { usage_breakdown: breakdown } = usageBreakdown;
  const usageTypes = ['started', 'benched', 'injured_list', 'other_roster', 'not_owned'];
  const statCategories = ['R', 'H', 'HR', 'RBI', 'SB', 'AVG', 'OBP', 'SLG'];

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Performance Breakdown
        </h2>
        <p className="text-gray-600">
          {playerName}'s statistical performance by roster status in {season}
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'overview'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('comparison')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'comparison'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Comparison
          </button>
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {usageTypes.map(usageType => {
            const data = breakdown[usageType];
            const stats = generateMockStats(usageType, data?.days || 0);
            
            if (!data || data.days === 0) return null;

            return (
              <div key={usageType} className={`border rounded-lg p-4 ${getUsageColor(usageType)}`}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">
                    {getUsageTitle(usageType)}
                  </h3>
                  <div className="text-sm">
                    <span className="font-medium">{data.percentage.toFixed(1)}%</span>
                    <span className="text-gray-600 ml-2">({data.days} days)</span>
                  </div>
                </div>

                {stats && (
                  <div className="grid grid-cols-4 md:grid-cols-8 gap-4">
                    {statCategories.map(stat => (
                      <div key={stat} className="text-center">
                        <div className="text-sm text-gray-600 mb-1">{stat}</div>
                        <div className="text-lg font-bold">
                          {formatStatValue(stat, stats[stat])}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {!stats && usageType !== 'not_owned' && (
                  <div className="text-center py-4">
                    <p className="text-sm text-gray-500">
                      Performance statistics will be available in future updates
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Comparison Tab */}
      {activeTab === 'comparison' && (
        <div>
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Statistical Comparison by Status
            </h3>
            <p className="text-sm text-gray-600">
              Compare performance across different roster situations
            </p>
          </div>

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
                  {statCategories.map(stat => (
                    <th key={stat} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {stat}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {usageTypes.map(usageType => {
                  const data = breakdown[usageType];
                  const stats = generateMockStats(usageType, data?.days || 0);
                  
                  if (!data || data.days === 0) return null;

                  return (
                    <tr key={usageType}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getUsageColor(usageType)}`}>
                          {getUsageTitle(usageType)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {data.days}
                      </td>
                      {statCategories.map(stat => (
                        <td key={stat} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stats ? formatStatValue(stat, stats[stat]) : '-'}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Performance Insights */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-medium text-blue-800 mb-1">
                  Performance Statistics Coming Soon
                </h4>
                <p className="text-sm text-blue-700">
                  Statistical performance data by roster status will be integrated with MLB data sources 
                  in future updates. This will include actual game stats when started vs benched.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PerformanceBreakdown;