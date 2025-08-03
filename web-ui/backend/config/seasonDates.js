/**
 * Season dates configuration for GKL Fantasy Baseball
 * Mirrors the Python SEASON_DATES configuration
 */

const SEASON_DATES = {
  2025: { start: '2025-03-27', end: '2025-09-28' },
  2024: { start: '2024-03-28', end: '2024-09-29' },
  2023: { start: '2023-03-30', end: '2023-10-01' },
  2022: { start: '2022-04-07', end: '2022-10-05' },
  2021: { start: '2021-04-01', end: '2021-10-03' },
  2020: { start: '2020-07-23', end: '2020-09-27' },
  2019: { start: '2019-03-28', end: '2019-09-29' },
  2018: { start: '2018-03-29', end: '2018-09-30' },
  2017: { start: '2017-04-02', end: '2017-10-01' },
  2016: { start: '2016-04-03', end: '2016-10-02' },
  2015: { start: '2015-04-05', end: '2015-10-04' },
  2014: { start: '2014-03-30', end: '2014-09-28' },
  2013: { start: '2013-03-31', end: '2013-09-29' },
  2012: { start: '2012-03-28', end: '2012-10-03' },
  2011: { start: '2011-03-31', end: '2011-09-28' },
  2010: { start: '2010-04-04', end: '2010-10-03' },
  2009: { start: '2009-04-05', end: '2009-10-04' },
  2008: { start: '2008-03-25', end: '2008-09-28' }
};

/**
 * Calculate the number of days between two dates (inclusive)
 */
function daysBetween(startDate, endDate) {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const diffTime = Math.abs(end - start);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays + 1; // Add 1 to make it inclusive
}

/**
 * Get the total number of days in a season up to today (or season end)
 */
function getSeasonDays(season) {
  const seasonData = SEASON_DATES[season];
  if (!seasonData) {
    throw new Error(`Season ${season} not found in configuration`);
  }
  
  const { start, end } = seasonData;
  const today = new Date().toISOString().split('T')[0];
  
  // Use the earlier of today or season end
  const effectiveEnd = today < end ? today : end;
  
  // If today is before season start, return 0
  if (today < start) {
    return 0;
  }
  
  return daysBetween(start, effectiveEnd);
}

/**
 * Get season date range
 */
function getSeasonDateRange(season) {
  const seasonData = SEASON_DATES[season];
  if (!seasonData) {
    throw new Error(`Season ${season} not found in configuration`);
  }
  return seasonData;
}

module.exports = {
  SEASON_DATES,
  getSeasonDays,
  getSeasonDateRange,
  daysBetween
};