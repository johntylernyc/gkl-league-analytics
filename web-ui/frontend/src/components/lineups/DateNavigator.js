import React from 'react';

const DateNavigator = ({ 
  selectedDate, 
  availableDates, 
  onDateChange, 
  onPrevious, 
  onNext,
  canGoPrevious,
  canGoNext 
}) => {
  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  return (
    <div className="flex items-center justify-between bg-white rounded-lg shadow px-4 py-3">
      <div className="flex items-center space-x-4">
        {/* Previous button */}
        <button
          onClick={onPrevious}
          disabled={!canGoPrevious}
          className={`p-2 rounded-lg transition-colors ${
            canGoPrevious 
              ? 'hover:bg-gray-100 text-gray-700' 
              : 'text-gray-300 cursor-not-allowed'
          }`}
          title="Previous day"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Current date display */}
        <div className="flex items-center space-x-2">
          <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-lg font-medium text-gray-900">
            {formatDate(selectedDate)}
          </span>
        </div>

        {/* Next button */}
        <button
          onClick={onNext}
          disabled={!canGoNext}
          className={`p-2 rounded-lg transition-colors ${
            canGoNext 
              ? 'hover:bg-gray-100 text-gray-700' 
              : 'text-gray-300 cursor-not-allowed'
          }`}
          title="Next day"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Date selector */}
      <div className="flex items-center space-x-2">
        <label htmlFor="date-select" className="text-sm text-gray-600">
          Jump to:
        </label>
        <select
          id="date-select"
          value={selectedDate || ''}
          onChange={(e) => onDateChange(e.target.value)}
          className="block w-40 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        >
          {availableDates.map(date => (
            <option key={date} value={date}>
              {new Date(date + 'T00:00:00').toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric' 
              })}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default DateNavigator;