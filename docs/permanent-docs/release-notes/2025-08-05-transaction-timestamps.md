# Enhanced Transaction Timestamps

**Release Date**: August 5, 2025  
**Version**: Transaction Timestamps Feature  
**Impact**: User Interface Enhancement

## What's New

### ⏰ Smarter Transaction Times

We've enhanced how transaction times are displayed throughout the application to give you better insight into when moves actually happened in your league.

#### Before vs After

**Before**: All transactions showed only the date (e.g., "Aug 05, 2025")

**After**: Recent transactions now show relative time with timezone information:
- **Today's moves**: "2 hours ago"
- **Recent moves**: "6:47 PM PDT" 
- **Older moves**: "Aug 05, 2025 6:47 PM PDT"

#### Where You'll See This

✅ **Transaction Explorer** (`/transactions`)
- More precise timing for recent waiver claims and trades
- Better understanding of when moves happened during the day

✅ **Home Dashboard** Recent transactions table
- Quick glance at the most recent league activity
- Relative timestamps help identify hot trading periods

#### Better Chronological Sorting

Transactions are now sorted by their exact timestamp (when available) rather than just the date. This means:

- Multiple transactions from the same day appear in the correct chronological order
- You can see the exact sequence of rapid-fire waiver claims or trades
- More accurate timeline of league activity throughout busy trading days

## Technical Details

This enhancement leverages timestamp data that was already being collected but not displayed. The feature:

- Uses your local timezone for display
- Maintains backward compatibility with older transactions
- Falls back gracefully to date-only display when timestamp data isn't available
- Improves the accuracy of transaction ordering in all views

## What's Next

This improvement lays the groundwork for future enhancements like:
- Timeline visualizations of trading activity
- Peak activity hour analysis
- More sophisticated league activity insights

---

*Having issues or questions about this update? Check our [implementation documentation](../development-docs/in-progress/improved-transaction-timestamps-implementation-plan.md) for technical details.*