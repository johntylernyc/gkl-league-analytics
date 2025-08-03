import React from 'react';

const ILScorecard = ({ usageBreakdown, monthlyData, playerName, season }) => {
  if (!usageBreakdown || !usageBreakdown.usage_breakdown) {
    return null;
  }

  const { usage_breakdown: breakdown, total_days } = usageBreakdown;
  const ilData = breakdown.injured_list || { days: 0, percentage: 0, positions: [] };

  // If no IL time, don't show the scorecard
  if (ilData.days === 0) {
    return null;
  }

  // Calculate IL metrics
  const ilPercentage = ilData.percentage || 0;
  const ilDays = ilData.days || 0;


  // Analyze IL stints from monthly data (excluding NA/minor leagues)
  let ilStints = [];
  if (monthlyData && monthlyData.length > 0) {
    monthlyData.forEach(month => {
      if (month.summary && month.summary.injured_list > 0) {
        ilStints.push({
          month: month.month,
          days: month.summary.injured_list,
          percentage: (month.summary.injured_list / month.total_days) * 100
        });
      }
    });
  }

  return (
    <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6 mb-8">
      {/* Header */}
      <div className="flex items-center mb-6">
        <div className="flex-shrink-0 mr-4">
          <div className="bg-red-100 rounded-full p-3">
            <svg className="h-8 w-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
        </div>
        <div className="flex-grow">
          <h2 className="text-2xl font-bold text-red-800 mb-1">
            Injured List Impact Scorecard
          </h2>
          <p className="text-red-700">
            {playerName} spent {ilDays} days ({ilPercentage.toFixed(1)}%) on the IL during {season}
          </p>
        </div>
      </div>

      {/* IL Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Total IL Time */}
        <div className="bg-white bg-opacity-70 rounded-lg p-4">
          <div className="text-3xl font-bold text-red-600 mb-1">
            {ilDays}
          </div>
          <div className="text-sm text-red-700 font-medium mb-1">Total IL Days</div>
          <div className="text-xs text-red-600">
            {ilPercentage.toFixed(1)}% of season
          </div>
        </div>

        {/* IL Months */}
        <div className="bg-white bg-opacity-70 rounded-lg p-4">
          <div className="text-3xl font-bold text-red-600 mb-1">
            {ilStints.length}
          </div>
          <div className="text-sm text-red-700 font-medium mb-1">IL Months</div>
          <div className="text-xs text-red-600">
            Months with IL time
          </div>
        </div>
      </div>


      {/* Monthly IL Timeline */}
      {ilStints.length > 0 && (
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-red-800 mb-3">IL Timeline by Month</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {ilStints.map((stint, index) => (
              <div key={index} className="bg-white bg-opacity-70 rounded-lg p-3">
                <div className="text-sm font-semibold text-red-800">{stint.month}</div>
                <div className="text-lg font-bold text-red-600">{stint.days} days</div>
                <div className="text-xs text-red-600">{stint.percentage.toFixed(0)}% of month</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Impact Analysis */}
      <div className="bg-red-100 border border-red-300 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-red-800">Fantasy Impact Analysis</h4>
            <p className="text-sm text-red-700 mt-1">
              {ilPercentage > 30 
                ? `High injury risk player - spent over 30% of season on IL. Consider injury-prone designation for future drafts.`
                : ilPercentage > 15 
                  ? `Moderate injury history - spent ${ilPercentage.toFixed(1)}% of season on IL. Monitor health status closely.`
                  : `Minor injury impact - spent only ${ilPercentage.toFixed(1)}% of season on IL. Generally reliable for fantasy.`
              }
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ILScorecard;