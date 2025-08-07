import React, { useState } from 'react';

const ReleaseNotes = ({ version, date, title, summary, highlights, details }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const hasDetails = details && (
    details.features?.length > 0 || 
    details.bugFixes?.length > 0 || 
    details.improvements?.length > 0
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              v{version}
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-3">{summary}</p>
        </div>
        <span className="text-sm text-gray-500 font-medium whitespace-nowrap ml-4">{date}</span>
      </div>
      
      <div className="space-y-2 mb-3">
        {highlights.map((highlight, i) => (
          <div key={i} className="flex items-start">
            <svg className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-sm text-gray-700">{highlight}</span>
          </div>
        ))}
      </div>
      
      {hasDetails && (
        <>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 transition-colors"
          >
            {isExpanded ? 'Show less' : 'Show more details'}
            <svg
              className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {isExpanded && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              {details.features?.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Features</h4>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    {details.features.map((feature, i) => (
                      <li key={i} className="text-sm text-gray-600">{feature}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {details.bugFixes?.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Bug Fixes</h4>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    {details.bugFixes.map((fix, i) => (
                      <li key={i} className="text-sm text-gray-600">{fix}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {details.improvements?.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Improvements</h4>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    {details.improvements.map((improvement, i) => (
                      <li key={i} className="text-sm text-gray-600">{improvement}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ReleaseNotes;