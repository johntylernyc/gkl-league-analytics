const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Connect to database
const dbPath = path.join(__dirname, '../../database/league_analytics.db');
const db = new sqlite3.Database(dbPath);

// Check what IL position types exist in the database
const testQuery = `
  SELECT DISTINCT selected_position, COUNT(*) as occurrences
  FROM daily_lineups
  WHERE selected_position IN ('IL', 'IL10', 'IL15', 'IL60', 'NA')
  GROUP BY selected_position
  ORDER BY selected_position
`;

console.log('Checking IL position types in database...\n');

db.all(testQuery, [], (err, rows) => {
  if (err) {
    console.error('Error:', err);
  } else {
    console.log('IL Position Types Found:');
    rows.forEach(row => {
      console.log(`  ${row.selected_position}: ${row.occurrences} total occurrences`);
    });
    
    if (rows.length === 0) {
      console.log('  No IL positions found in database');
    }
  }
  
  // Now check for specific players with IL time
  const playerQuery = `
    SELECT 
      player_name,
      selected_position,
      COUNT(*) as days
    FROM daily_lineups
    WHERE selected_position IN ('IL', 'IL10', 'IL15', 'IL60', 'NA')
    AND strftime('%Y', date) = '2025'
    GROUP BY player_name, selected_position
    ORDER BY days DESC
    LIMIT 10
  `;
  
  console.log('\nTop 10 players with IL time in 2025:');
  db.all(playerQuery, [], (err, rows) => {
    if (err) {
      console.error('Error:', err);
    } else {
      rows.forEach(row => {
        console.log(`  ${row.player_name}: ${row.selected_position} for ${row.days} days`);
      });
    }
    db.close();
  });
});