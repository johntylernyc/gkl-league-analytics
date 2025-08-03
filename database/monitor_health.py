"""
Real-time database health monitoring for SQLite optimizations.
"""
import sqlite3
import time
import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DatabaseHealthMonitor:
    """
    Monitor database health metrics.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize monitor with database path.
        
        Args:
            db_path: Path to database file, or None to auto-detect
        """
        if db_path is None:
            db_path = self._find_database()
        
        self.db_path = db_path
        self.metrics = []
        self.alert_thresholds = {
            'lock_rate_per_min': 5,
            'transaction_failure_rate': 0.01,
            'response_time_ms': 100,
            'wal_size_mb': 100,
            'fragmentation_percent': 20
        }
        
    def _find_database(self) -> str:
        """Find the database file to monitor."""
        # Try to import database configuration
        try:
            from config.database_config import get_database_path, get_environment
            env = get_environment()
            return str(get_database_path(env))
        except ImportError:
            pass
        
        # Fallback to known locations
        possible_paths = [
            'database/league_analytics.db',
            'database/league_analytics_test.db',
            '../database/league_analytics.db',
            '../database/league_analytics_test.db'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("Could not find database file. Please specify path.")
    
    def collect_metrics(self) -> Dict:
        """
        Collect current health metrics.
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'database': self.db_path,
            'alerts': [],
            'metrics': {}
        }
        
        if not os.path.exists(self.db_path):
            metrics['error'] = f"Database file not found: {self.db_path}"
            metrics['alerts'].append("Database file missing!")
            return metrics
        
        try:
            # Get file system metrics
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
            metrics['metrics']['database_size_mb'] = round(db_size_mb, 2)
            
            # Check for WAL file
            wal_file = self.db_path + '-wal'
            if os.path.exists(wal_file):
                wal_size_mb = os.path.getsize(wal_file) / (1024 * 1024)
                metrics['metrics']['wal_size_mb'] = round(wal_size_mb, 2)
                
                if wal_size_mb > self.alert_thresholds['wal_size_mb']:
                    metrics['alerts'].append(f"WAL size high: {wal_size_mb:.1f} MB")
            
            # Check for SHM file
            shm_file = self.db_path + '-shm'
            if os.path.exists(shm_file):
                shm_size_kb = os.path.getsize(shm_file) / 1024
                metrics['metrics']['shm_size_kb'] = round(shm_size_kb, 2)
            
            # Connect to database for internal metrics
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cursor = conn.cursor()
            
            # Get PRAGMA settings
            pragmas = ['journal_mode', 'synchronous', 'busy_timeout', 'cache_size', 'page_size', 'page_count']
            for pragma in pragmas:
                try:
                    result = cursor.execute(f"PRAGMA {pragma}").fetchone()
                    if result:
                        metrics['metrics'][f'pragma_{pragma}'] = result[0]
                except:
                    pass
            
            # Calculate database fragmentation
            if 'pragma_page_count' in metrics['metrics'] and 'pragma_page_size' in metrics['metrics']:
                page_count = metrics['metrics']['pragma_page_count']
                page_size = metrics['metrics']['pragma_page_size']
                
                # Get freelist count
                freelist_count = cursor.execute("PRAGMA freelist_count").fetchone()[0]
                metrics['metrics']['freelist_count'] = freelist_count
                
                if page_count > 0:
                    fragmentation = (freelist_count / page_count) * 100
                    metrics['metrics']['fragmentation_percent'] = round(fragmentation, 2)
                    
                    if fragmentation > self.alert_thresholds['fragmentation_percent']:
                        metrics['alerts'].append(f"High fragmentation: {fragmentation:.1f}%")
            
            # Get table statistics
            tables = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            
            table_stats = {}
            for table_name, in tables:
                try:
                    count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    table_stats[table_name] = count
                except:
                    pass
            
            metrics['metrics']['table_rows'] = table_stats
            
            # Check for lock status (try a write operation)
            try:
                start = time.time()
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute("ROLLBACK")
                write_time_ms = (time.time() - start) * 1000
                metrics['metrics']['write_test_ms'] = round(write_time_ms, 2)
                
                if write_time_ms > self.alert_thresholds['response_time_ms']:
                    metrics['alerts'].append(f"Slow write response: {write_time_ms:.0f}ms")
            except sqlite3.OperationalError as e:
                if "locked" in str(e):
                    metrics['alerts'].append("Database is locked!")
                    metrics['metrics']['database_locked'] = True
            
            conn.close()
            
            # Check feature flags if available
            try:
                from database.feature_flags import get_feature_flags
                flags = get_feature_flags()
                enabled_features = [f for f, enabled in flags.flags.items() if enabled]
                metrics['metrics']['enabled_features'] = enabled_features
            except ImportError:
                pass
            
            # Check for recent lock events if monitoring is active
            try:
                from database.db_utils import get_lock_monitor
                lock_monitor = get_lock_monitor()
                lock_stats = lock_monitor.get_stats()
                
                metrics['metrics']['recent_locks_1min'] = lock_stats['recent_locks_1min']
                metrics['metrics']['locks_per_minute'] = round(lock_stats['locks_per_minute'], 2)
                
                if lock_stats['locks_per_minute'] > self.alert_thresholds['lock_rate_per_min']:
                    metrics['alerts'].append(f"High lock rate: {lock_stats['locks_per_minute']:.1f}/min")
            except:
                pass
            
        except Exception as e:
            metrics['error'] = str(e)
            metrics['alerts'].append(f"Collection error: {e}")
        
        return metrics
    
    def monitor_continuous(self, interval: int = 60, duration: Optional[int] = None):
        """
        Continuously monitor database health.
        
        Args:
            interval: Seconds between checks
            duration: Total monitoring duration in seconds (None for infinite)
        """
        print(f"Starting continuous monitoring of: {self.db_path}")
        print(f"Interval: {interval}s")
        if duration:
            print(f"Duration: {duration}s")
        print("Press Ctrl+C to stop\n")
        
        start_time = time.time()
        
        try:
            while True:
                metrics = self.collect_metrics()
                self._display_metrics(metrics)
                self.metrics.append(metrics)
                
                # Check if duration exceeded
                if duration and (time.time() - start_time) > duration:
                    print("\nMonitoring duration reached")
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        
        # Save metrics on exit
        if self.metrics:
            self.save_metrics()
    
    def _display_metrics(self, metrics: Dict):
        """Display metrics in a readable format."""
        timestamp = metrics['timestamp'].split('T')[1].split('.')[0]  # Just time
        
        print(f"\n[{timestamp}] Database Health Check")
        print("-" * 50)
        
        if 'error' in metrics:
            print(f"❌ ERROR: {metrics['error']}")
            return
        
        # Display key metrics
        m = metrics['metrics']
        
        # Basic info
        print(f"📁 Database: {os.path.basename(self.db_path)}")
        print(f"   Size: {m.get('database_size_mb', 'N/A')} MB")
        
        if 'pragma_journal_mode' in m:
            mode = m['pragma_journal_mode']
            print(f"   Journal Mode: {mode}")
            
            if mode == 'wal' and 'wal_size_mb' in m:
                wal_size = m['wal_size_mb']
                wal_indicator = "⚠️" if wal_size > 50 else "✅"
                print(f"   WAL Size: {wal_indicator} {wal_size} MB")
        
        # Performance metrics
        if 'write_test_ms' in m:
            write_time = m['write_test_ms']
            write_indicator = "✅" if write_time < 100 else "⚠️"
            print(f"   Write Test: {write_indicator} {write_time:.1f}ms")
        
        if 'fragmentation_percent' in m:
            frag = m['fragmentation_percent']
            frag_indicator = "✅" if frag < 10 else "⚠️" if frag < 20 else "❌"
            print(f"   Fragmentation: {frag_indicator} {frag:.1f}%")
        
        # Lock statistics
        if 'recent_locks_1min' in m:
            locks = m['recent_locks_1min']
            lock_rate = m.get('locks_per_minute', 0)
            lock_indicator = "✅" if locks == 0 else "⚠️" if locks < 5 else "❌"
            print(f"   Recent Locks: {lock_indicator} {locks} (rate: {lock_rate:.1f}/min)")
        
        # Table statistics
        if 'table_rows' in m:
            print("\n📊 Table Statistics:")
            for table, count in m['table_rows'].items():
                print(f"   {table}: {count:,} rows")
        
        # Enabled features
        if 'enabled_features' in m and m['enabled_features']:
            print(f"\n⚙️ Enabled Features: {', '.join(m['enabled_features'])}")
        
        # Alerts
        if metrics['alerts']:
            print("\n⚠️ ALERTS:")
            for alert in metrics['alerts']:
                print(f"   - {alert}")
        else:
            print("\n✅ All metrics within normal range")
    
    def save_metrics(self, filename: Optional[str] = None):
        """Save collected metrics to file."""
        if not self.metrics:
            print("No metrics to save")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"database/health_metrics_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        print(f"\n📄 Metrics saved to: {filename}")
        
        # Generate summary
        self._generate_summary()
    
    def _generate_summary(self):
        """Generate summary of collected metrics."""
        if not self.metrics:
            return
        
        print("\n" + "="*50)
        print("MONITORING SUMMARY")
        print("="*50)
        
        # Time range
        start = self.metrics[0]['timestamp']
        end = self.metrics[-1]['timestamp']
        print(f"Period: {start} to {end}")
        print(f"Samples: {len(self.metrics)}")
        
        # Alert summary
        all_alerts = []
        for m in self.metrics:
            all_alerts.extend(m.get('alerts', []))
        
        if all_alerts:
            print(f"\nTotal Alerts: {len(all_alerts)}")
            # Count by type
            alert_types = {}
            for alert in all_alerts:
                alert_type = alert.split(':')[0]
                alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
            
            print("Alert Types:")
            for atype, count in sorted(alert_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {atype}: {count}")
        else:
            print("\n✅ No alerts during monitoring period")
        
        # Performance summary
        write_times = [m['metrics'].get('write_test_ms', 0) 
                      for m in self.metrics 
                      if 'write_test_ms' in m.get('metrics', {})]
        
        if write_times:
            avg_write = sum(write_times) / len(write_times)
            max_write = max(write_times)
            min_write = min(write_times)
            
            print(f"\nWrite Performance:")
            print(f"   Average: {avg_write:.1f}ms")
            print(f"   Min: {min_write:.1f}ms")
            print(f"   Max: {max_write:.1f}ms")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Monitor SQLite database health')
    parser.add_argument('--database', '-d', help='Path to database file')
    parser.add_argument('--interval', '-i', type=int, default=60,
                       help='Monitoring interval in seconds (default: 60)')
    parser.add_argument('--duration', type=int,
                       help='Total monitoring duration in seconds')
    parser.add_argument('--once', action='store_true',
                       help='Run single health check and exit')
    parser.add_argument('--save', help='Save metrics to specified file')
    parser.add_argument('--thresholds', action='store_true',
                       help='Show alert thresholds')
    
    args = parser.parse_args()
    
    # Initialize monitor
    try:
        monitor = DatabaseHealthMonitor(args.database)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please specify database path with --database option")
        return 1
    
    # Show thresholds if requested
    if args.thresholds:
        print("Alert Thresholds:")
        for key, value in monitor.alert_thresholds.items():
            print(f"   {key}: {value}")
        return 0
    
    # Run monitoring
    if args.once:
        # Single check
        metrics = monitor.collect_metrics()
        monitor._display_metrics(metrics)
        
        if args.save:
            monitor.metrics = [metrics]
            monitor.save_metrics(args.save)
    else:
        # Continuous monitoring
        monitor.monitor_continuous(args.interval, args.duration)
        
        if args.save:
            monitor.save_metrics(args.save)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())