import React from 'react';

const Managers = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Manager Analysis</h1>
        <div className="text-sm text-gray-500">Coming Soon</div>
      </div>

      <div className="card">
        <div className="card-body text-center py-12">
          <div className="text-6xl text-gray-300 mb-6">👥</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">
            Manager Analytics Module Under Development
          </h3>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            Detailed manager analysis and performance metrics will be available here, including:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-lg mx-auto text-left">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Trading frequency analysis</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-success-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Player acquisition patterns</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-warning-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Activity level tracking</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Performance metrics</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Manager Rankings</h3>
          </div>
          <div className="card-body">
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((rank) => (
                <div key={rank} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-medium text-gray-500">#{rank}</span>
                    <span className="text-sm text-gray-900">Manager {rank}</span>
                  </div>
                  <span className="text-sm text-gray-500">-- transactions</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Activity Timeline</h3>
          </div>
          <div className="card-body">
            <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-500">Timeline Placeholder</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Trading Patterns</h3>
          </div>
          <div className="card-body">
            <div className="h-32 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-500">Patterns Placeholder</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Managers;