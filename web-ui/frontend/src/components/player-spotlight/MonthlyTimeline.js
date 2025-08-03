import React, { useState } from 'react';

const MonthlyTimeline = ({ monthlyData, season, playerName }) => {
  const [hoveredMonth, setHoveredMonth] = useState(null);

  // Color mapping for different status types
  const getStatusColor = (status) => {
    if (['BN'].includes(status)) return 'bg-orange-400'; // Benched
    if (['IL', 'IL10', 'IL15', 'IL60', 'NA'].includes(status)) return 'bg-red-400'; // Injured/IL
    if (status === 'Not Owned' || status === 'FA') return 'bg-gray-400'; // Not Owned
    return 'bg-green-400'; // Started (active positions)
  };

  const getStatusLabel = (status) => {
    if (['BN'].includes(status)) return 'Benched';
    if (['IL', 'IL10', 'IL15', 'IL60', 'NA'].includes(status)) return 'Injured/IL';
    if (status === 'Not Owned' || status === 'FA') return 'Not Owned';
    return 'Started';
  };

  // Generate timeline bars for each month
  const generateTimelineBar = (monthData) => {
    if (!monthData.positions || monthData.positions.length === 0) {
      return (
        <div className="h-6 bg-gray-200 rounded flex items-center justify-center">
          <span className="text-xs text-gray-500">No data</span>
        </div>
      );
    }

    const totalDays = monthData.total_days;
    const segments = [];

    monthData.positions.forEach((pos, index) => {
      const percentage = (pos.days / totalDays) * 100;
      const color = getStatusColor(pos.position);
      
      segments.push(
        <div
          key={index}
          className={`${color} h-full flex items-center justify-center relative group`}
          style={{ width: `${percentage}%` }}
          title={`${pos.position}: ${pos.days} days`}
        >
          {percentage > 15 && (
            <span className="text-xs font-medium text-white">
              {pos.days}
            </span>
          )}
        </div>
      );
    });

    return (
      <div className="h-6 bg-gray-200 rounded flex overflow-hidden">
        {segments}
      </div>
    );
  };

  const formatMonthYear = (monthData) => {
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

      {/* Legend */}
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
          <div className="w-4 h-4 bg-gray-400 rounded mr-2"></div>
          <span>Not Owned</span>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-4">
        {monthlyData.map((monthData, index) => (
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
                <span>{monthData.summary.started} started</span>
                <span className="mx-1">/</span>
                <span>{monthData.summary.benched} benched</span>
                {monthData.summary.injured_list > 0 && (
                  <>
                    <span className="mx-1">/</span>
                    <span>{monthData.summary.injured_list} injured</span>
                  </>
                )}
                {monthData.summary.other_roster > 0 && (
                  <>
                    <span className="mx-1">/</span>
                    <span>{monthData.summary.other_roster} other roster</span>
                  </>
                )}
                {monthData.summary.not_owned > 0 && (
                  <>
                    <span className="mx-1">/</span>
                    <span>{monthData.summary.not_owned} not owned</span>
                  </>
                )}
              </div>
            </div>

            {/* Timeline Bar */}
            <div className="relative">
              {generateTimelineBar(monthData)}
              
              {/* Hover Tooltip */}
              {hoveredMonth === index && (
                <div className="absolute z-10 left-0 top-8 bg-black bg-opacity-75 text-white text-xs rounded p-2 whitespace-nowrap">
                  <div className="font-medium mb-1">{formatMonthYear(monthData)}</div>
                  {monthData.positions.map((pos, posIndex) => (
                    <div key={posIndex} className="flex justify-between">
                      <span className="mr-3">{pos.position}:</span>
                      <span>{pos.days} days</span>
                    </div>
                  ))}
                  <div className="border-t border-gray-400 mt-1 pt-1">
                    <div className="flex justify-between font-medium">
                      <span>Total:</span>
                      <span>{monthData.total_days} days</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
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
              📊 Timeline shows data through {monthlyData[monthlyData.length - 1]?.latest_date || 'current date'}. 
              Future dates will become available as the season progresses.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MonthlyTimeline;