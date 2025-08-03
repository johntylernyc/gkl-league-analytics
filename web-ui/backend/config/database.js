/**
 * Database configuration for Node.js backend
 * This module provides environment-aware database path configuration
 * that mirrors the Python config.database_config module
 */

const path = require('path');

// Database file names
const PRODUCTION_DB = 'league_analytics.db';
const TEST_DB = 'league_analytics_test.db';

// Default environment
const DEFAULT_ENVIRONMENT = 'production';

// Base path to database directory
const DATABASE_DIR = path.resolve(__dirname, '../../../database');

/**
 * Get the current environment setting
 * @param {string} override - Optional environment override ('test' or 'production')
 * @returns {string} The environment ('test' or 'production')
 */
function getEnvironment(override) {
  if (override) {
    return override.toLowerCase();
  }
  
  // Check environment variable
  const env = (process.env.DATA_ENV || DEFAULT_ENVIRONMENT).toLowerCase();
  
  // Validate environment
  if (env !== 'test' && env !== 'production') {
    console.warn(`Warning: Invalid DATA_ENV '${env}', using 'production'`);
    return 'production';
  }
  
  return env;
}

/**
 * Get the appropriate database path based on environment
 * @param {string} environment - Optional environment override ('test' or 'production')
 * @returns {string} Full path to the database file
 */
function getDatabasePath(environment) {
  const env = getEnvironment(environment);
  
  if (env === 'test') {
    return path.join(DATABASE_DIR, TEST_DB);
  } else {
    return path.join(DATABASE_DIR, PRODUCTION_DB);
  }
}

/**
 * Get the table suffix for the environment
 * @param {string} environment - Optional environment override
 * @returns {string} Table suffix ('_test' or '_production')
 */
function getTableSuffix(environment) {
  const env = getEnvironment(environment);
  
  if (env === 'test') {
    return '_test';
  } else {
    return '_production';
  }
}

/**
 * Get the full table name for the environment
 * @param {string} baseName - Base table name (e.g., 'transactions', 'daily_lineups')
 * @param {string} environment - Optional environment override
 * @returns {string} Full table name with environment suffix
 */
function getTableName(baseName, environment) {
  const env = getEnvironment(environment);
  const suffix = getTableSuffix(env);
  
  // Special handling for certain tables
  if (baseName === 'transactions') {
    // Production uses 'transactions', test uses 'transactions_test'
    if (env === 'test') {
      return `${baseName}_test`;
    } else {
      return baseName;
    }
  } else if (baseName === 'daily_lineups') {
    // Daily lineups doesn't use suffix pattern currently
    if (env === 'test') {
      return `${baseName}_test`;
    } else {
      return baseName;
    }
  } else if (baseName === 'job_log') {
    // Job log is shared
    return baseName;
  } else {
    // Default behavior for other tables
    if (env === 'test') {
      return `${baseName}_test`;
    } else {
      return baseName;
    }
  }
}

/**
 * Check if we're in test environment
 * @param {string} environment - Optional environment override
 * @returns {boolean} True if test environment
 */
function isTestEnvironment(environment) {
  return getEnvironment(environment) === 'test';
}

/**
 * Check if we're in production environment
 * @param {string} environment - Optional environment override
 * @returns {boolean} True if production environment
 */
function isProductionEnvironment(environment) {
  return getEnvironment(environment) === 'production';
}

module.exports = {
  getDatabasePath,
  getTableName,
  getTableSuffix,
  getEnvironment,
  isTestEnvironment,
  isProductionEnvironment,
  DATABASE_DIR,
  PRODUCTION_DB,
  TEST_DB
};