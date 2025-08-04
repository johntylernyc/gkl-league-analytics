#!/usr/bin/env node

/**
 * Export SQLite database to SQL files for D1 migration
 */

const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, '../../database/league_analytics.db');
const OUTPUT_DIR = path.join(__dirname, '../sql');

// Create output directory
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

console.log('Exporting database from:', DB_PATH);
console.log('Output directory:', OUTPUT_DIR);

const db = new sqlite3.Database(DB_PATH, sqlite3.OPEN_READONLY);

// Tables to export
const TABLES = [
  'transactions',
  'transaction_players',
  'teams',
  'daily_lineups',
  'daily_gkl_player_stats',
  'player_id_mapping',
  'job_log',
  'error_log'
];

async function exportSchema() {
  return new Promise((resolve, reject) => {
    let schema = '-- Database Schema for Cloudflare D1\n\n';
    
    db.serialize(() => {
      let completed = 0;
      
      TABLES.forEach(table => {
        db.get(
          `SELECT sql FROM sqlite_master WHERE type='table' AND name=?`,
          [table],
          (err, row) => {
            if (err) {
              console.error(`Error getting schema for ${table}:`, err);
            } else if (row) {
              // Clean up schema for D1 compatibility
              let cleanedSql = row.sql
                .replace(/AUTOINCREMENT/gi, '')
                .replace(/INTEGER PRIMARY KEY/gi, 'INTEGER PRIMARY KEY')
                .replace(/WITHOUT ROWID/gi, '');
              
              schema += `-- Table: ${table}\n`;
              schema += cleanedSql + ';\n\n';
            }
            
            completed++;
            if (completed === TABLES.length) {
              fs.writeFileSync(path.join(OUTPUT_DIR, 'schema.sql'), schema);
              console.log('Schema exported to schema.sql');
              resolve();
            }
          }
        );
      });
    });
  });
}

async function exportData() {
  console.log('Exporting data...');
  
  for (const table of TABLES) {
    await new Promise((resolve, reject) => {
      db.all(`SELECT * FROM ${table}`, (err, rows) => {
        if (err) {
          console.error(`Error exporting ${table}:`, err);
          resolve();
          return;
        }
        
        if (rows.length === 0) {
          console.log(`${table}: No data to export`);
          resolve();
          return;
        }
        
        let data = `-- Data for table: ${table}\n`;
        const batchSize = 100;
        
        for (let i = 0; i < rows.length; i += batchSize) {
          const batch = rows.slice(i, i + batchSize);
          
          batch.forEach(row => {
            const columns = Object.keys(row);
            const values = columns.map(col => {
              const val = row[col];
              if (val === null) return 'NULL';
              if (typeof val === 'string') return `'${val.replace(/'/g, "''")}'`;
              return val;
            });
            
            data += `INSERT INTO ${table} (${columns.join(', ')}) VALUES (${values.join(', ')});\n`;
          });
        }
        
        const filename = `data_${table}.sql`;
        fs.writeFileSync(path.join(OUTPUT_DIR, filename), data);
        console.log(`${table}: Exported ${rows.length} rows to ${filename}`);
        resolve();
      });
    });
  }
}

async function createIndexes() {
  const indexes = `
-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_team ON transactions(team_key);
CREATE INDEX IF NOT EXISTS idx_transaction_players_tid ON transaction_players(transaction_id);
CREATE INDEX IF NOT EXISTS idx_transaction_players_player ON transaction_players(player_name);
CREATE INDEX IF NOT EXISTS idx_lineups_date ON daily_lineups(date);
CREATE INDEX IF NOT EXISTS idx_lineups_team ON daily_lineups(team_key);
CREATE INDEX IF NOT EXISTS idx_lineups_player ON daily_lineups(player_key);
CREATE INDEX IF NOT EXISTS idx_player_stats_date ON daily_gkl_player_stats(date);
CREATE INDEX IF NOT EXISTS idx_player_stats_mlb_id ON daily_gkl_player_stats(mlb_player_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_yahoo_id ON daily_gkl_player_stats(yahoo_player_id);
`;

  fs.writeFileSync(path.join(OUTPUT_DIR, 'indexes.sql'), indexes);
  console.log('Indexes exported to indexes.sql');
}

async function main() {
  try {
    await exportSchema();
    await exportData();
    await createIndexes();
    
    console.log('\n✅ Database export completed!');
    console.log(`\nSQL files created in: ${OUTPUT_DIR}`);
    console.log('\nNext steps:');
    console.log('1. Create D1 database: wrangler d1 create gkl-fantasy');
    console.log('2. Import schema: wrangler d1 execute gkl-fantasy --file=sql/schema.sql');
    console.log('3. Import data: Run the import-to-d1.js script');
    
  } catch (error) {
    console.error('Export failed:', error);
    process.exit(1);
  } finally {
    db.close();
  }
}

main();