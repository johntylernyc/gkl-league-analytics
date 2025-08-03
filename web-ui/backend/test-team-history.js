const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Connect to database
const dbPath = path.join(__dirname, '../../database/league_analytics.db');
const db = new sqlite3.Database(dbPath);

// Test query for Paul Skenes team history
const testQuery = `
  SELECT 
    COUNT(*) as days, 
    team_name,
    MIN(date) as first_date,
    MAX(date) as last_date
  FROM daily_lineups
  WHERE player_id = '62972' 
  AND strftime('%Y', date) = '2025'
  GROUP BY team_name
  ORDER BY first_date
`;

console.log('Paul Skenes team history in 2025:\n');

db.all(testQuery, [], (err, rows) => {
  if (err) {
    console.error('Error:', err);
  } else {
    console.log('Team History:');
    rows.forEach(row => {
      console.log(`  ${row.team_name}: ${row.days} days (${row.first_date} to ${row.last_date})`);
    });
    
    const totalDays = rows.reduce((sum, row) => sum + row.days, 0);
    console.log(`\nTotal days tracked: ${totalDays}`);
    
    // Show percentages
    console.log('\nOwnership percentages:');
    rows.forEach(row => {
      const percentage = (row.days / totalDays * 100).toFixed(1);
      console.log(`  ${row.team_name}: ${percentage}%`);
    });
  }
  db.close();
});