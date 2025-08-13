#!/usr/bin/env node
/**
 * Update Backend Column Names
 * Updates all references from player_id to yahoo_player_id in Node.js backend services
 */

const fs = require('fs');
const path = require('path');

// Files to update
const filesToUpdate = [
  'web-ui/backend/services/transactionService.js',
  'web-ui/backend/services/lineupService.js',
  'web-ui/backend/services/playerStatsService.js',
  'web-ui/backend/services/playerService.js',
  'web-ui/backend/services/playerSpotlightService.js'
];

// Patterns to replace in SQL queries
const replacements = [
  // SQL column references
  { from: /\bplayer_id\b(?!\w)/g, to: 'yahoo_player_id' },
  // JavaScript property references in SQL results
  { from: /\.player_id\b/g, to: '.yahoo_player_id' },
  { from: /\['player_id'\]/g, to: "['yahoo_player_id']" },
  // Object property definitions
  { from: /player_id:/g, to: 'yahoo_player_id:' }
];

// Special case for player_id_mapping table name (shouldn't be changed)
const preservePatterns = [
  /player_id_mapping/g
];

function updateFile(filePath) {
  const fullPath = path.join(__dirname, '..', filePath);
  
  if (!fs.existsSync(fullPath)) {
    console.log(`[SKIP] File not found: ${filePath}`);
    return;
  }
  
  let content = fs.readFileSync(fullPath, 'utf8');
  const originalContent = content;
  
  // Temporarily replace patterns we want to preserve
  const preservedReplacements = [];
  preservePatterns.forEach((pattern, index) => {
    const placeholder = `__PRESERVE_${index}__`;
    const matches = content.match(pattern);
    if (matches) {
      preservedReplacements.push({ placeholder, original: matches[0] });
      content = content.replace(pattern, placeholder);
    }
  });
  
  // Apply replacements
  let changeCount = 0;
  replacements.forEach(({ from, to }) => {
    const matches = content.match(from);
    if (matches) {
      changeCount += matches.length;
      content = content.replace(from, to);
    }
  });
  
  // Restore preserved patterns
  preservedReplacements.forEach(({ placeholder, original }) => {
    content = content.replace(new RegExp(placeholder, 'g'), original);
  });
  
  if (content !== originalContent) {
    // Create backup
    const backupPath = fullPath + '.backup';
    fs.writeFileSync(backupPath, originalContent);
    
    // Write updated content
    fs.writeFileSync(fullPath, content);
    console.log(`[OK] Updated ${filePath} (${changeCount} replacements)`);
  } else {
    console.log(`[SKIP] No changes needed: ${filePath}`);
  }
}

console.log('Updating backend services to use yahoo_player_id...\n');

filesToUpdate.forEach(updateFile);

console.log('\n[SUCCESS] Backend column name updates complete!');
console.log('Note: Backup files created with .backup extension');
console.log('\nNext steps:');
console.log('1. Test the backend locally: cd web-ui/backend && npm start');
console.log('2. Verify API endpoints work correctly');
console.log('3. Remove backup files when confirmed: rm web-ui/backend/services/*.backup');