#!/usr/bin/env python3
"""
Incremental Player Stats Update Script

Handles daily incremental updates of MLB player statistics with Yahoo ID refresh.
Designed for automation via cron or GitHub Actions.

Usage:
    # Default: Update last 7 days to test database
    python update_stats.py
    
    # Update last 3 days to production
    python update_stats.py --days 3 --environment production
    
    # Update specific date with D1
    python update_stats.py --date 2024-08-05 --use-d1
    
    # Update since last date in database
    python update_stats.py --since-last
    
    # Also refresh Yahoo IDs
    python update_stats.py --refresh-yahoo
    
    # Quiet mode for automation
    python update_stats.py --quiet
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, date, timedelta

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.comprehensive_collector import ComprehensiveStatsCollector
from data_pipeline.player_stats.yahoo_id_matcher import YahooIDMatcher
from data_pipeline.player_stats.yahoo_player_search import YahooPlayerSearch

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlayerStatsUpdater:
    """Handles incremental updates of player statistics with Yahoo ID refresh"""
    
    def __init__(self, environment='production', use_d1=False):
        """
        Initialize updater.
        
        Args:
            environment: 'test' or 'production' for local databases
            use_d1: If True, write to Cloudflare D1
        """
        self.environment = environment
        self.use_d1 = use_d1
        
        # Initialize components
        self.collector = ComprehensiveStatsCollector(environment=environment)
        self.yahoo_matcher = YahooIDMatcher(environment=environment)
        self.yahoo_search = YahooPlayerSearch(environment=environment)
        
        # D1 connection if needed
        if use_d1:
            from data_pipeline.common.d1_connection import D1Connection
            self.d1_conn = D1Connection()
        else:
            self.d1_conn = None
        
        logger.info(f"Initialized updater for {environment} {'with D1' if use_d1 else 'with SQLite'}")
    
    def get_date_range(self, days: int = None, specific_date: str = None, 
                      since_last: bool = False) -> tuple:
        """
        Determine date range for update.
        
        Args:
            days: Number of days to look back
            specific_date: Specific date to update (YYYY-MM-DD)
            since_last: Update since last date in database
            
        Returns:
            Tuple of (start_date, end_date)
        """
        if specific_date:
            # Single date
            target = datetime.strptime(specific_date, '%Y-%m-%d').date()
            return target, target
            
        elif since_last:
            # Since last date in database
            cursor = self.collector.conn.cursor()
            cursor.execute("SELECT MAX(date) FROM daily_gkl_player_stats")
            result = cursor.fetchone()
            
            if result and result[0]:
                last_date = datetime.strptime(result[0], '%Y-%m-%d').date()
                start = last_date + timedelta(days=1)
                end = date.today() - timedelta(days=1)  # Yesterday
                
                if start > end:
                    logger.info("Database is already up to date")
                    return None, None
                    
                return start, end
            else:
                # No data, use default lookback
                end = date.today() - timedelta(days=1)
                start = end - timedelta(days=6)  # Default 7 days
                return start, end
                
        else:
            # Default lookback
            end = date.today() - timedelta(days=1)  # Yesterday
            start = end - timedelta(days=(days - 1) if days else 6)
            return start, end
    
    def update_stats(self, start_date: date, end_date: date, refresh_yahoo: bool = False):
        """
        Update stats for date range.
        
        Args:
            start_date: Start date
            end_date: End date
            refresh_yahoo: Whether to refresh Yahoo IDs
        """
        if not start_date or not end_date:
            return
        
        logger.info(f"Updating stats from {start_date} to {end_date}")
        
        # Initialize player mappings if needed (skip for D1 - handled separately)
        if not self.use_d1:
            cursor = self.collector.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM player_mapping")
            if cursor.fetchone()[0] == 0:
                logger.info("Initializing player mappings...")
                self.collector.initialize_player_mappings()
        
        # Collect stats for each date
        total_records = 0
        current = start_date
        
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            logger.info(f"Collecting stats for {date_str}")
            
            try:
                records = self.collector.collect_daily_stats(date_str)
                total_records += records
                logger.info(f"  Collected {records} player records")
                
                # Write to D1 if enabled
                if self.use_d1 and records > 0:
                    self._write_to_d1(date_str)
                    
            except Exception as e:
                logger.error(f"  Error collecting stats for {date_str}: {e}")
            
            current += timedelta(days=1)
        
        logger.info(f"Total records collected: {total_records}")
        
        # Refresh Yahoo IDs if requested
        if refresh_yahoo:
            self.refresh_yahoo_ids()
        
        # Update Yahoo IDs in daily stats (skip for D1)
        if not self.use_d1:
            self._update_daily_stats_yahoo_ids()
    
    def refresh_yahoo_ids(self):
        """Refresh Yahoo IDs for unmapped players"""
        logger.info("Refreshing Yahoo IDs...")
        
        cursor = self.collector.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM player_mapping 
            WHERE yahoo_player_id IS NULL 
            AND active = 1
        """)
        unmapped_count = cursor.fetchone()[0]
        
        if unmapped_count == 0:
            logger.info("All active players have Yahoo IDs!")
            return
        
        logger.info(f"Found {unmapped_count} players without Yahoo IDs")
        
        try:
            if unmapped_count < 100:
                # Small number - search individually
                logger.info("Using individual search")
                stats = self.yahoo_search.backfill_missing_yahoo_ids()
                logger.info(f"Found {stats['found']} new Yahoo IDs")
            else:
                # Large number - use bulk methods
                logger.info("Using bulk matching")
                
                # First try matching from league data
                self.yahoo_matcher.build_yahoo_player_registry()
                matches = self.yahoo_matcher.match_yahoo_to_mlb(threshold=0.80)
                updated = self.yahoo_matcher.update_player_mappings(matches)
                logger.info(f"Matched {updated} players from league data")
                
                # Check if we need API calls
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM player_mapping 
                    WHERE yahoo_player_id IS NULL 
                    AND active = 1
                """)
                still_unmapped = cursor.fetchone()[0]
                
                if still_unmapped > 50:
                    logger.info(f"Still {still_unmapped} unmapped, fetching from Yahoo API...")
                    matched = self.yahoo_search.bulk_import_yahoo_players()
                    logger.info(f"Matched {matched} additional players from Yahoo API")
                    
        except Exception as e:
            logger.error(f"Error refreshing Yahoo IDs: {e}")
    
    def _update_daily_stats_yahoo_ids(self):
        """Update Yahoo IDs in daily_gkl_player_stats from player_mapping"""
        try:
            # Use correct column name based on environment
            mlb_id_column = 'mlb_player_id' if self.environment == 'production' else 'mlb_id'
            
            query = f"""
                UPDATE daily_gkl_player_stats
                SET yahoo_player_id = (
                    SELECT pm.yahoo_player_id 
                    FROM player_mapping pm 
                    WHERE pm.mlb_id = daily_gkl_player_stats.{mlb_id_column}
                )
                WHERE yahoo_player_id IS NULL
                OR yahoo_player_id != (
                    SELECT pm.yahoo_player_id 
                    FROM player_mapping pm 
                    WHERE pm.mlb_id = daily_gkl_player_stats.{mlb_id_column}
                )
            """
            
            cursor = self.collector.conn.cursor()
            cursor.execute(query)
            updated = cursor.rowcount
            self.collector.conn.commit()
            
            if updated > 0:
                logger.info(f"Updated {updated} Yahoo IDs in daily stats")
                
        except Exception as e:
            logger.error(f"Error updating Yahoo IDs: {e}")
    
    def _write_to_d1(self, date_str: str):
        """Write collected data to D1"""
        try:
            cursor = self.collector.conn.cursor()
            
            # Get daily stats for this date
            cursor.execute(
                "SELECT * FROM daily_gkl_player_stats WHERE date = ?",
                (date_str,)
            )
            stats = cursor.fetchall()
            
            if stats:
                # Write in chunks to respect D1 limits
                chunk_size = 50
                for i in range(0, len(stats), chunk_size):
                    chunk = stats[i:i+chunk_size]
                    placeholders = ",".join(["(?" + ",?" * (len(chunk[0])-1) + ")"] * len(chunk))
                    values = [item for row in chunk for item in row]
                    
                    self.d1_conn.execute(
                        f"INSERT OR REPLACE INTO daily_gkl_player_stats VALUES {placeholders}",
                        values
                    )
                
                logger.info(f"  Wrote {len(stats)} records to D1")
                
        except Exception as e:
            logger.error(f"Error writing to D1: {e}")
    
    def show_summary(self):
        """Show summary statistics"""
        cursor = self.collector.conn.cursor()
        
        # Player mapping stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(yahoo_player_id) as with_yahoo,
                ROUND(COUNT(yahoo_player_id) * 100.0 / COUNT(*), 1) as pct
            FROM player_mapping 
            WHERE active = 1
        """)
        mapping = cursor.fetchone()
        
        # Daily stats
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT date) as days,
                COUNT(*) as total_records,
                MIN(date) as first_date,
                MAX(date) as last_date,
                COUNT(yahoo_player_id) as with_yahoo,
                ROUND(COUNT(yahoo_player_id) * 100.0 / COUNT(*), 1) as yahoo_pct
            FROM daily_gkl_player_stats
        """)
        stats = cursor.fetchone()
        
        print("\n" + "="*60)
        print("UPDATE SUMMARY")
        print("="*60)
        print(f"\nPlayer Mappings:")
        print(f"  Active MLB players: {mapping[0]}")
        print(f"  With Yahoo IDs: {mapping[1]} ({mapping[2]}%)")
        
        if stats[0]:
            print(f"\nDaily Stats:")
            print(f"  Date range: {stats[2]} to {stats[3]}")
            print(f"  Days of data: {stats[0]}")
            print(f"  Total records: {stats[1]}")
            print(f"  With Yahoo IDs: {stats[4]} ({stats[5]}%)")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Update player statistics incrementally',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Date options
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to look back (default: 7)')
    parser.add_argument('--date', help='Specific date to update (YYYY-MM-DD)')
    parser.add_argument('--since-last', action='store_true',
                       help='Update since last date in database')
    
    # Database options
    parser.add_argument('--environment', default='production',
                       choices=['test', 'production'],
                       help='Database environment (default: production)')
    parser.add_argument('--use-d1', action='store_true',
                       help='Also write to Cloudflare D1')
    
    # Processing options
    parser.add_argument('--refresh-yahoo', action='store_true',
                       help='Refresh Yahoo IDs for unmapped players')
    parser.add_argument('--quiet', action='store_true',
                       help='Minimal output for automation')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Initialize updater
    updater = PlayerStatsUpdater(
        environment=args.environment,
        use_d1=args.use_d1
    )
    
    # Get date range
    start_date, end_date = updater.get_date_range(
        days=args.days,
        specific_date=args.date,
        since_last=args.since_last
    )
    
    if start_date is None:
        if not args.quiet:
            print("No dates to update")
        return
    
    # Run update
    updater.update_stats(start_date, end_date, refresh_yahoo=args.refresh_yahoo)
    
    # Show summary unless quiet
    if not args.quiet:
        updater.show_summary()


if __name__ == '__main__':
    main()