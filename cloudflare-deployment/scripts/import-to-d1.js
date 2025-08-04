#!/usr/bin/env node

/**
 * Import SQL files to Cloudflare D1 database
 */

const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const SQL_DIR = path.join(__dirname, '../sql');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(prompt) {
  return new Promise(resolve => {
    rl.question(prompt, resolve);
  });
}

async function executeWranglerCommand(command) {
  return new Promise((resolve, reject) => {
    console.log(`Executing: ${command}`);
    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error: ${error.message}`);
        reject(error);
        return;
      }
      if (stderr) {
        console.error(`Warning: ${stderr}`);
      }
      console.log(stdout);
      resolve(stdout);
    });
  });
}

async function main() {
  console.log('=== Cloudflare D1 Database Import ===\n');
  
  // Check if SQL files exist
  if (!fs.existsSync(SQL_DIR)) {
    console.error(`SQL directory not found: ${SQL_DIR}`);
    console.log('Please run export-database.js first');
    process.exit(1);
  }
  
  const databaseName = await question('Enter D1 database name (or press Enter for "gkl-fantasy"): ') || 'gkl-fantasy';
  
  console.log('\nImport process will:');
  console.log('1. Create database (if not exists)');
  console.log('2. Import schema');
  console.log('3. Import data');
  console.log('4. Create indexes\n');
  
  const proceed = await question('Continue? (y/n): ');
  if (proceed.toLowerCase() !== 'y') {
    console.log('Import cancelled');
    process.exit(0);
  }
  
  try {
    // Step 1: Create database
    console.log('\n📦 Creating D1 database...');
    try {
      const createResult = await executeWranglerCommand(`wrangler d1 create ${databaseName}`);
      console.log('Database created successfully');
      
      // Extract database ID from output
      const idMatch = createResult.match(/database_id = "([^"]+)"/);
      if (idMatch) {
        console.log(`\n⚠️  Add this to your wrangler.toml:`);
        console.log(`database_id = "${idMatch[1]}"`);
      }
    } catch (error) {
      console.log('Database might already exist, continuing...');
    }
    
    // Step 2: Import schema
    console.log('\n📋 Importing schema...');
    const schemaFile = path.join(SQL_DIR, 'schema.sql');
    if (fs.existsSync(schemaFile)) {
      await executeWranglerCommand(`wrangler d1 execute ${databaseName} --file=${schemaFile}`);
      console.log('Schema imported successfully');
    } else {
      console.log('Schema file not found, skipping...');
    }
    
    // Step 3: Import data files
    console.log('\n📊 Importing data...');
    const dataFiles = fs.readdirSync(SQL_DIR).filter(f => f.startsWith('data_'));
    
    for (const file of dataFiles) {
      const tableName = file.replace('data_', '').replace('.sql', '');
      console.log(`Importing ${tableName}...`);
      
      const filePath = path.join(SQL_DIR, file);
      const fileContent = fs.readFileSync(filePath, 'utf8');
      const statements = fileContent.split(';\n').filter(s => s.trim());
      
      // Split into smaller batches for D1 limits
      const batchSize = 50;
      for (let i = 0; i < statements.length; i += batchSize) {
        const batch = statements.slice(i, i + batchSize).join(';\n') + ';';
        const tempFile = path.join(SQL_DIR, 'temp_batch.sql');
        fs.writeFileSync(tempFile, batch);
        
        try {
          await executeWranglerCommand(`wrangler d1 execute ${databaseName} --file=${tempFile}`);
          console.log(`  Batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(statements.length/batchSize)} completed`);
        } catch (error) {
          console.error(`  Error in batch ${Math.floor(i/batchSize) + 1}: ${error.message}`);
        }
        
        fs.unlinkSync(tempFile);
      }
    }
    
    // Step 4: Create indexes
    console.log('\n🔍 Creating indexes...');
    const indexFile = path.join(SQL_DIR, 'indexes.sql');
    if (fs.existsSync(indexFile)) {
      await executeWranglerCommand(`wrangler d1 execute ${databaseName} --file=${indexFile}`);
      console.log('Indexes created successfully');
    }
    
    console.log('\n✅ Import completed successfully!');
    console.log('\nNext steps:');
    console.log('1. Update wrangler.toml with the database_id');
    console.log('2. Test the API: wrangler dev');
    console.log('3. Deploy to production: wrangler publish');
    
  } catch (error) {
    console.error('\n❌ Import failed:', error.message);
    process.exit(1);
  } finally {
    rl.close();
  }
}

main();