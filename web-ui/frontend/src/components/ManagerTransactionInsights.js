import React, { useState } from 'react';

const ManagerTransactionInsights = ({ managerStats }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!managerStats || managerStats.length === 0) {
    return null;
  }

  // Find the maximum transaction count for scaling
  const maxTransactions = Math.max(...managerStats.map(m => m.transaction_count));
  
  return (
    <div className="card">
      <div className="card-body">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Manager Activity</h3>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                Hide Details
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
              </>
            ) : (
              <>
                Show Details
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </>
            )}
          </button>
        </div>
        
        {/* Summary Stats - Always Visible */}
        <div className="grid grid-cols-3 gap-4 text-center mb-4">
          <div>
            <div className="text-sm text-gray-500">Most Active</div>
            <div className="text-sm font-semibold text-gray-900 truncate">
              {managerStats[0]?.team_name}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Average</div>
            <div className="text-sm font-semibold text-gray-900">
              {Math.round(managerStats.reduce((sum, m) => sum + m.transaction_count, 0) / managerStats.length)}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Total Managers</div>
            <div className="text-sm font-semibold text-gray-900">
              {managerStats.length}
            </div>
          </div>
        </div>

        {/* Detailed Manager List - Collapsible */}
        {isExpanded && (
          <div className="space-y-3 pt-4 border-t border-gray-200 animate-fadeIn">
            {managerStats.map((manager, index) => {
              const percentage = (manager.transaction_count / maxTransactions) * 100;
              return (
                <div key={index} className="group">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-gray-700 truncate max-w-xs">
                      {manager.team_name}
                    </span>
                    <span className="text-sm font-semibold text-gray-900 ml-2">
                      {manager.transaction_count}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full transition-all duration-500 ease-out hover:from-blue-500 hover:to-blue-700"
                      style={{ width: `${percentage}%` }}
                      title={`${manager.team_name}: ${manager.transaction_count} transactions`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ManagerTransactionInsights;