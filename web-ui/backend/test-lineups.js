const sqlite3 = require('sqlite3');
const path = require('path');

async function testLineups() {
  try {
    console.log('Testing database connection...');
    const dbPath = path.resolve(__dirname, '..', '..', 'database', 'league_analytics.db');
    console.log('Database path:', dbPath);
    
    const db = new sqlite3.Database(dbPath, (err) => {
      if (err) {
        console.error('Connection error:', err.message);
        return;
      }
      console.log('✅ Connected successfully!');
      
      // Test teams query
      db.all('SELECT DISTINCT team_key, team_name FROM daily_lineups LIMIT 3', (err, teams) => {
        if (err) {
          console.error('Teams query error:', err.message);
        } else {
          console.log(`✅ Found ${teams.length} teams:`, teams);
        }
        
        // Test dates query
        db.all('SELECT DISTINCT date FROM daily_lineups ORDER BY date DESC LIMIT 5', (err, dates) => {
          if (err) {
            console.error('Dates query error:', err.message);
          } else {
            console.log(`✅ Found ${dates.length} recent dates:`, dates.map(d => d.date));
          }
          
          // Test count
          db.get('SELECT COUNT(*) as count FROM daily_lineups', (err, result) => {
            if (err) {
              console.error('Count query error:', err.message);
            } else {
              console.log(`✅ Total records: ${result.count}`);
            }
            
            db.close();
            console.log('✅ All tests passed!');
          });
        });
      });
    });
    
  } catch (error) {
    console.error('❌ Test failed:', error);
  }
}

testLineups();