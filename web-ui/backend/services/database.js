const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const { getDatabasePath, getEnvironment } = require('../config/database');

class Database {
  constructor() {
    this.db = null;
    this.environment = getEnvironment();
  }

  connect(environment) {
    return new Promise((resolve, reject) => {
      // Allow environment override or use default
      const env = environment || this.environment;
      const dbPath = getDatabasePath(env);
      
      this.db = new sqlite3.Database(dbPath, (err) => {
        if (err) {
          console.error('Error connecting to SQLite database:', err.message);
          reject(err);
        } else {
          console.log(`Connected to SQLite database (${env}):`, dbPath);
          resolve();
        }
      });
    });
  }

  close() {
    return new Promise((resolve, reject) => {
      if (this.db) {
        this.db.close((err) => {
          if (err) {
            reject(err);
          } else {
            console.log('Database connection closed');
            resolve();
          }
        });
      } else {
        resolve();
      }
    });
  }

  // Execute a query that returns multiple rows
  all(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  // Execute a query that returns a single row
  get(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.get(sql, params, (err, row) => {
        if (err) {
          reject(err);
        } else {
          resolve(row);
        }
      });
    });
  }

  // Execute a query that doesn't return data
  run(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function(err) {
        if (err) {
          reject(err);
        } else {
          resolve({ lastID: this.lastID, changes: this.changes });
        }
      });
    });
  }
}

// Create singleton instance
const database = new Database();

module.exports = database;