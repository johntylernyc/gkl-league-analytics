import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import apiService from '../services/api';
import { formatTransactionDateTime } from '../utils/dateFormatters';

const Home = () => {
  const [stats, setStats] = useState(null);
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch stats
        const statsData = await apiService.getTransactionStats();
        setStats(statsData);
        
        // Fetch recent transactions (10 most recent)
        const transactionsData = await apiService.getTransactions({ limit: 10 });
        setRecentTransactions(transactionsData.transactions || []);
      } catch (error) {
        console.error('Failed to fetch home page data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy');
    } catch {
      return dateString;
    }
  };

  const getDisplayDateTime = (transaction) => {
    // Use timestamp if available, otherwise fall back to date only
    if (transaction.timestamp) {
      return formatTransactionDateTime(transaction.timestamp);
    }
    // Fallback for transactions without timestamp
    return {
      dateLine: formatDate(transaction.date),
      timeLine: ''
    };
  };

  const getMovementTypeColor = (type) => {
    switch (type?.toLowerCase()) {
      case 'add':
        return 'bg-success-100 text-success-800';
      case 'drop':
        return 'bg-red-100 text-red-800';
      case 'trade':
        return 'bg-primary-100 text-primary-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mt-12">
        <div className="card h-full">
          <div className="card-body text-center flex flex-col h-full">
            <div className="text-3xl text-primary-500 mb-4">📊</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Transaction Explorer
            </h3>
            <p className="text-gray-600 mb-4 flex-grow">
              Browse and search through all fantasy transactions with advanced filtering.
            </p>
            <a href="/transactions" className="btn-primary w-full text-center">
              Explore Moves
            </a>
          </div>
        </div>

        <div className="card h-full">
          <div className="card-body text-center flex flex-col h-full">
            <div className="text-3xl text-purple-500 mb-4">📋</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Daily Lineups
            </h3>
            <p className="text-gray-600 mb-4 flex-grow">
              View and analyze daily roster decisions and lineup optimizations.
            </p>
            <a href="/lineups" className="btn-primary w-full text-center">
              View Lineups
            </a>
          </div>
        </div>

        <div className="card h-full">
          <div className="card-body text-center flex flex-col h-full">
            <div className="text-3xl text-indigo-500 mb-4">🔍</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Player Explorer
            </h3>
            <p className="text-gray-600 mb-4 flex-grow">
              Search players and view detailed spotlight cards with stats.
            </p>
            <a href="/players" className="btn-primary w-full text-center">
              Explore Players
            </a>
          </div>
        </div>

        <div className="card h-full">
          <div className="card-body text-center flex flex-col h-full">
            <div className="text-3xl text-success-500 mb-4">📈</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Analytics Dashboard
            </h3>
            <p className="text-gray-600 mb-4 flex-grow">
              View trends, patterns, and insights from league transaction data.
            </p>
            <button disabled className="btn-secondary w-full text-center">
              Coming Soon
            </button>
          </div>
        </div>

        <div className="card h-full">
          <div className="card-body text-center flex flex-col h-full">
            <div className="text-3xl text-warning-500 mb-4">👥</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Manager Analysis
            </h3>
            <p className="text-gray-600 mb-4 flex-grow">
              Analyze individual manager trading patterns and activity.
            </p>
            <button disabled className="btn-secondary w-full text-center">
              Coming Soon
            </button>
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
              <div className="text-2xl font-bold text-primary-600">
                {loading ? '--' : (stats?.overview?.total_transactions || 0).toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">Total Transactions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-success-600">
                {loading ? '--' : stats?.managerStats?.length || 0}
              </div>
              <div className="text-sm text-gray-500">Active Managers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-warning-600">
                {loading ? '--' : (stats?.overview?.unique_players || 0).toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">Unique Players</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">2025</div>
              <div className="text-sm text-gray-500">Season</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Transactions Table */}
      <div className="card mt-6">
        <div className="card-header">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-900">
              Recent Transactions
            </h2>
            <a href="/transactions" className="text-sm text-primary-600 hover:text-primary-700">
              View All →
            </a>
          </div>
        </div>
        <div className="card-body p-0">
          {loading ? (
            <div className="p-6 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading recent transactions...</p>
            </div>
          ) : recentTransactions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="table">
                <thead className="table-header">
                  <tr>
                    <th className="table-header-cell">Date</th>
                    <th className="table-header-cell">Player</th>
                    <th className="table-header-cell">Position</th>
                    <th className="table-header-cell">MLB Team</th>
                    <th className="table-header-cell">Movement</th>
                    <th className="table-header-cell">From</th>
                    <th className="table-header-cell">To</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {recentTransactions.map((transaction) => {
                    const dateTime = getDisplayDateTime(transaction);
                    return (
                    <tr key={transaction.id} className="hover:bg-gray-50">
                      <td className="table-cell text-gray-900">
                        <div className="flex flex-col">
                          <span className="text-sm">{dateTime.dateLine}</span>
                          <span className="text-xs text-gray-500">{dateTime.timeLine}</span>
                        </div>
                      </td>
                      <td className="table-cell">
                        <div className="font-medium text-gray-900">
                          {transaction.player_name}
                        </div>
                      </td>
                      <td className="table-cell">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          {transaction.player_position || 'N/A'}
                        </span>
                      </td>
                      <td className="table-cell text-gray-900">
                        {transaction.player_team || 'N/A'}
                      </td>
                      <td className="table-cell">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMovementTypeColor(transaction.movement_type)}`}>
                          {transaction.movement_type || 'N/A'}
                        </span>
                      </td>
                      <td className="table-cell text-gray-900 text-sm">
                        {transaction.source_team_name || 'Free Agency'}
                      </td>
                      <td className="table-cell text-gray-900 text-sm">
                        {transaction.destination_team_name || 'Free Agency'}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-6 text-center text-gray-500">
              No recent transactions found
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Home;