const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Connect to database
const dbPath = path.join(__dirname, '../../database/league_analytics.db');
const db = new sqlite3.Database(dbPath);

// Test the month name query
const testQuery = `
  SELECT 
    strftime('%Y-%m', date) as month_year,
    CASE strftime('%m', date)
      WHEN '01' THEN 'January'
      WHEN '02' THEN 'February'
      WHEN '03' THEN 'March'
      WHEN '04' THEN 'April'
      WHEN '05' THEN 'May'
      WHEN '06' THEN 'June'
      WHEN '07' THEN 'July'
      WHEN '08' THEN 'August'
      WHEN '09' THEN 'September'
      WHEN '10' THEN 'October'
      WHEN '11' THEN 'November'
      WHEN '12' THEN 'December'
    END as month_name,
    COUNT(*) as count
  FROM daily_lineups
  WHERE player_id = '8861' 
  AND strftime('%Y', date) = '2025'
  GROUP BY month_year, month_name
  ORDER BY month_year
`;

console.log('Testing month name extraction...\n');

db.all(testQuery, [], (err, rows) => {
  if (err) {
    console.error('Error:', err);
  } else {
    console.log('Results:');
    rows.forEach(row => {
      console.log(`${row.month_year}: ${row.month_name} (${row.count} records)`);
    });
  }
  db.close();
});