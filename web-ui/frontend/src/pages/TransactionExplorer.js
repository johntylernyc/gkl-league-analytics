import React, { useState, useEffect } from 'react';
import { useTransactions } from '../hooks/useTransactions';
import TransactionFilters from '../components/TransactionFilters';
import TransactionTable from '../components/TransactionTable';
import Pagination from '../components/Pagination';
import ManagerTransactionInsights from '../components/ManagerTransactionInsights';
import apiService from '../services/api';

const TransactionExplorer = () => {
  const [stats, setStats] = useState(null);
  const {
    transactions,
    loading,
    error,
    pagination,
    filters,
    updateFilters,
    changePage,
    changeLimit,
    resetFilters
  } = useTransactions();

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await apiService.getTransactionStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch transaction stats:', error);
      }
    };
    fetchStats();
  }, []);

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Transaction Explorer</h1>
        <div className="card">
          <div className="card-body text-center py-12">
            <div className="text-red-400 text-5xl mb-4">⚠️</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Transactions</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="btn-primary"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transaction Explorer</h1>
          <p className="text-gray-600 mt-1">
            Browse and analyze fantasy baseball transaction data
          </p>
        </div>
      </div>

      {/* Stats Overview */}
      {stats && stats.overview && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-primary-600">
                  {stats.overview.total_transactions?.toLocaleString() || 0}
                </div>
                <div className="text-sm text-gray-500">Total Transactions</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-success-600">
                  {stats.overview.unique_players?.toLocaleString() || 0}
                </div>
                <div className="text-sm text-gray-500">Unique Players</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                {stats.mostDroppedPlayer ? (
                  <div className="text-xl font-bold text-warning-600 truncate">
                    {stats.mostDroppedPlayer.player_name}
                  </div>
                ) : (
                  <div className="text-2xl font-bold text-warning-600">N/A</div>
                )}
                <div className="text-sm text-gray-500 mt-1">Most Dropped Player</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-2xl font-bold text-gray-600">
                  {stats.overview.earliest_date && stats.overview.latest_date ? (
                    <>
                      {new Date(stats.overview.earliest_date).getFullYear()}
                      {new Date(stats.overview.earliest_date).getFullYear() !== new Date(stats.overview.latest_date).getFullYear() && 
                        ` - ${new Date(stats.overview.latest_date).getFullYear()}`
                      }
                    </>
                  ) : (
                    '2025'
                  )}
                </div>
                <div className="text-sm text-gray-500">Season</div>
              </div>
            </div>
          </div>
          
          {/* Manager Transaction Insights */}
          {stats.managerStats && stats.managerStats.length > 0 && (
            <ManagerTransactionInsights managerStats={stats.managerStats} />
          )}
        </>
      )}

      {/* Filters */}
      <TransactionFilters
        filters={filters}
        onFiltersChange={updateFilters}
        onReset={resetFilters}
      />

      {/* Results Summary */}
      <div className="flex justify-between items-center">
        <div className="text-sm text-gray-600">
          {loading ? 'Loading...' : `${pagination.total} rows`}
        </div>
        {Object.keys(filters).some(key => filters[key]) && (
          <button
            onClick={resetFilters}
            className="text-sm text-primary-600 hover:text-primary-700"
          >
            Clear all filters
          </button>
        )}
      </div>

      {/* Transaction Table */}
      <TransactionTable transactions={transactions} loading={loading} />

      {/* Pagination */}
      <Pagination
        pagination={pagination}
        onPageChange={changePage}
        onLimitChange={changeLimit}
      />
    </div>
  );
};

export default TransactionExplorer;