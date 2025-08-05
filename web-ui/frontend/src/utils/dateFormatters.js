import { format, isToday, differenceInHours } from 'date-fns';

/**
 * Format a timestamp into a structured date/time object with user's timezone
 * Yahoo Fantasy timestamps are stored in Pacific Time (PT)
 * @param {number|string} timestamp - Unix timestamp or date string
 * @returns {object} Object with dateLine and timeLine properties
 */
export const formatTransactionDateTime = (timestamp) => {
  if (!timestamp) {
    return {
      dateLine: 'Unknown date',
      timeLine: ''
    };
  }
  
  try {
    // Handle both Unix timestamps and date strings
    // Unix timestamps are already in UTC, so no timezone adjustment needed
    const date = typeof timestamp === 'number' && timestamp > 0 
      ? new Date(timestamp * 1000)  // Unix timestamp (seconds)
      : new Date(timestamp);
    
    if (isNaN(date.getTime())) {
      return {
        dateLine: 'Invalid date',
        timeLine: ''
      };
    }
    
    // Get user's timezone
    const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    // Get timezone abbreviation - use 'long' format and extract common abbreviations
    const longTz = new Intl.DateTimeFormat('en-US', {
      timeZone: userTimeZone,
      timeZoneName: 'long'
    }).formatToParts(date).find(part => part.type === 'timeZoneName')?.value || '';
    
    // Map common long timezone names to abbreviations
    const tzMap = {
      'British Summer Time': 'BST',
      'Greenwich Mean Time': 'GMT',
      'Eastern Standard Time': 'EST',
      'Eastern Daylight Time': 'EDT',
      'Central Standard Time': 'CST',
      'Central Daylight Time': 'CDT',
      'Mountain Standard Time': 'MST',
      'Mountain Daylight Time': 'MDT',
      'Pacific Standard Time': 'PST',
      'Pacific Daylight Time': 'PDT',
      'Central European Time': 'CET',
      'Central European Summer Time': 'CEST'
    };
    
    // Try to get a clean abbreviation
    let tzAbbr = tzMap[longTz];
    
    if (!tzAbbr) {
      // Fallback: try to get short name, but clean up GMT offsets
      tzAbbr = new Intl.DateTimeFormat('en-US', {
        timeZone: userTimeZone,
        timeZoneName: 'short'
      }).formatToParts(date).find(part => part.type === 'timeZoneName')?.value || 'TZ';
      
      // If it's a GMT offset, try to determine if it's BST based on the offset
      if (tzAbbr.startsWith('GMT') && userTimeZone === 'Europe/London') {
        const offset = date.getTimezoneOffset();
        tzAbbr = offset === -60 ? 'BST' : 'GMT';
      }
    }
    
    // Check if transaction is from today
    if (isToday(date)) {
      // For today's transactions, show relative time
      const hoursAgo = differenceInHours(new Date(), date);
      return {
        dateLine: format(date, 'MMM dd, yyyy'),
        timeLine: hoursAgo === 0 ? 'Just now' : `${hoursAgo} hours ago`
      };
    }
    
    // For all other transactions, show date and time in user's timezone
    return {
      dateLine: format(date, 'MMM dd, yyyy'),
      timeLine: `${format(date, 'h:mm a')} ${tzAbbr}`
    };
  } catch (error) {
    console.error('Error formatting timestamp:', error);
    return {
      dateLine: 'Invalid date',
      timeLine: ''
    };
  }
};

/**
 * Format a date for display (backward compatibility)
 * @param {string} dateString - Date string
 * @returns {string} Formatted date
 */
export const formatDate = (dateString) => {
  try {
    return format(new Date(dateString), 'MMM dd, yyyy');
  } catch {
    return dateString;
  }
};