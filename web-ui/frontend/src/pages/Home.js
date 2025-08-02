import React from 'react';

const Home = () => {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Welcome to GKL League Analytics
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Explore fantasy baseball transaction data, analyze trading patterns, 
          and gain insights into league activity and manager performance.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
        <div className="card">
          <div className="card-body text-center">
            <div className="text-3xl text-primary-500 mb-4">📊</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Transaction Explorer
            </h3>
            <p className="text-gray-600 mb-4">
              Browse and search through all fantasy transactions with advanced filtering options.
            </p>
            <a href="/transactions" className="btn-primary">
              Explore Transactions
            </a>
          </div>
        </div>

        <div className="card">
          <div className="card-body text-center">
            <div className="text-3xl text-success-500 mb-4">📈</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Analytics Dashboard
            </h3>
            <p className="text-gray-600 mb-4">
              View trends, patterns, and insights from league transaction data.
            </p>
            <a href="/analytics" className="btn-secondary">
              Coming Soon
            </a>
          </div>
        </div>

        <div className="card">
          <div className="card-body text-center">
            <div className="text-3xl text-warning-500 mb-4">👥</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Manager Analysis
            </h3>
            <p className="text-gray-600 mb-4">
              Analyze individual manager trading patterns and activity levels.
            </p>
            <a href="/managers" className="btn-secondary">
              Coming Soon
            </a>
          </div>
        </div>
      </div>

      <div className="card mt-12">
        <div className="card-header">
          <h2 className="text-xl font-semibold text-gray-900">
            Recent Activity Overview
          </h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">777</div>
              <div className="text-sm text-gray-500">Total Transactions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-success-600">--</div>
              <div className="text-sm text-gray-500">Active Managers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-warning-600">--</div>
              <div className="text-sm text-gray-500">Player Moves</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">2025</div>
              <div className="text-sm text-gray-500">Season</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;