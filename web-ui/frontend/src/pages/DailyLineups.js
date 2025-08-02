import React from 'react';

const DailyLineups = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Daily Lineups</h1>
        <div className="text-sm text-gray-500">Coming Soon</div>
      </div>

      <div className="card">
        <div className="card-body text-center py-12">
          <div className="text-6xl text-gray-300 mb-6">⚾</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">
            Daily Lineup Tracking Coming Soon
          </h3>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            Track daily lineup decisions, analyze playing time patterns, and optimize your roster management.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-lg mx-auto text-left">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Daily roster snapshots</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-success-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Bench utilization metrics</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-warning-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Playing time analysis</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Optimal lineup suggestions</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Active Rosters</h3>
          </div>
          <div className="card-body">
            <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-500">Feature Placeholder</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Bench Analysis</h3>
          </div>
          <div className="card-body">
            <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-500">Feature Placeholder</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Lineup Optimization</h3>
          </div>
          <div className="card-body">
            <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-500">Feature Placeholder</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DailyLineups;