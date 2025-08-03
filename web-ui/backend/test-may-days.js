const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Connect to database
const dbPath = path.join(__dirname, '../../database/league_analytics.db');
const db = new sqlite3.Database(dbPath);

// Test query for Yordan Alvarez May data
const testQuery = `
  SELECT 
    strftime('%Y-%m', date) as month_year,
    CASE strftime('%m', date)
      WHEN '05' THEN 'May'
    END as month_name,
    COUNT(DISTINCT date) as total_days_in_month,
    selected_position,
    COUNT(*) as position_days
  FROM daily_lineups
  WHERE player_id = '7163' 
  AND strftime('%Y', date) = '2025'
  AND strftime('%m', date) = '05'
  GROUP BY month_year, month_name, selected_position
  ORDER BY position_days DESC
`;

console.log('Testing Yordan Alvarez May 2025 data...\n');

db.all(testQuery, [], (err, rows) => {
  if (err) {
    console.error('Error:', err);
  } else {
    console.log('Results:');
    let totalDaysInMay = 0;
    let ilDays = 0;
    
    rows.forEach(row => {
      console.log(`Position: ${row.selected_position}, Days: ${row.position_days}`);
      if (row.total_days_in_month > totalDaysInMay) {
        totalDaysInMay = row.total_days_in_month;
      }
      if (['IL', 'IL10', 'IL15', 'IL60', 'NA'].includes(row.selected_position)) {
        ilDays += row.position_days;
      }
    });
    
    console.log(`\nTotal unique days in May: ${totalDaysInMay}`);
    console.log(`IL days: ${ilDays}`);
    console.log(`IL percentage: ${((ilDays / totalDaysInMay) * 100).toFixed(1)}%`);
  }
  db.close();
});