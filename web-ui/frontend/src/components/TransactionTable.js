import React from 'react';
import { format } from 'date-fns';

const TransactionTable = ({ transactions, loading }) => {
  if (loading) {
    return (
      <div className="card">
        <div className="card-body text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading transactions...</p>
        </div>
      </div>
    );
  }

  if (!transactions || transactions.length === 0) {
    return (
      <div className="card">
        <div className="card-body text-center py-12">
          <div className="text-gray-400 text-5xl mb-4">📄</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No transactions found</h3>
          <p className="text-gray-600">Try adjusting your filters to see more results.</p>
        </div>
      </div>
    );
  }

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy');
    } catch {
      return dateString;
    }
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
    <div className="card">
      <div className="overflow-x-auto">
        <table className="table">
          <thead className="table-header">
            <tr>
              <th className="table-header-cell">Date</th>
              <th className="table-header-cell">Player</th>
              <th className="table-header-cell">Position</th>
              <th className="table-header-cell">MLB Team</th>
              <th className="table-header-cell">Transaction</th>
              <th className="table-header-cell">Movement</th>
              <th className="table-header-cell">From Team</th>
              <th className="table-header-cell">To Team</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {transactions.map((transaction) => (
              <tr key={transaction.id} className="hover:bg-gray-50">
                <td className="table-cell text-gray-900">
                  {formatDate(transaction.date)}
                </td>
                <td className="table-cell">
                  <div className="font-medium text-gray-900">
                    {transaction.player_name}
                  </div>
                  <div className="text-xs text-gray-500">
                    ID: {transaction.player_id}
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
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {transaction.transaction_type}
                  </span>
                </td>
                <td className="table-cell">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMovementTypeColor(transaction.movement_type)}`}>
                    {transaction.movement_type || 'N/A'}
                  </span>
                </td>
                <td className="table-cell text-gray-900">
                  <div className="max-w-xs truncate">
                    {transaction.source_team_name || 'N/A'}
                  </div>
                  {transaction.source_team_key && (
                    <div className="text-xs text-gray-500">
                      {transaction.source_team_key}
                    </div>
                  )}
                </td>
                <td className="table-cell text-gray-900">
                  <div className="max-w-xs truncate">
                    {transaction.destination_team_name || 'N/A'}
                  </div>
                  {transaction.destination_team_key && (
                    <div className="text-xs text-gray-500">
                      {transaction.destination_team_key}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TransactionTable;