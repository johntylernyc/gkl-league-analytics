import React from 'react';

const Analytics = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
        <div className="text-sm text-gray-500">Coming Soon</div>
      </div>

      <div className="card">
        <div className="card-body text-center py-12">
          <div className="text-6xl text-gray-300 mb-6">📈</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">
            Analytics Module Under Development
          </h3>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            Advanced analytics and insights will be available here soon, including:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-lg mx-auto text-left">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Trading pattern analysis</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-success-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Player value trends</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-warning-500 rounded-full"></div>
              <span className="text-sm text-gray-700">League activity metrics</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Manager performance</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Transaction Trends</h3>
          </div>
          <div className="card-body">
            <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-500">Chart Placeholder</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Top Players</h3>
          </div>
          <div className="card-body">
            <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-500">List Placeholder</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Activity Heat Map</h3>
          </div>
          <div className="card-body">
            <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-500">Heat Map Placeholder</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;