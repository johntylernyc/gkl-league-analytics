"""
Emergency rollback script for database optimizations.
Use this script to immediately disable all optimization features if issues occur.
"""
import json
import sqlite3
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def rollback_all_features():
    """
    Disable all optimization features immediately.
    """
    print("\n⚠️ EMERGENCY ROLLBACK INITIATED")
    print("="*50)
    
    # Try to import and disable feature flags
    try:
        from database.feature_flags import DatabaseFeatureFlags
        flags = DatabaseFeatureFlags()
        
        print("\nDisabling all optimization features...")
        features_disabled = []
        
        for feature in flags.flags:
            if flags.flags[feature]:
                print(f"  Disabling: {feature}")
                flags.flags[feature] = False
                features_disabled.append(feature)
        
        flags.save_flags()
        
        if features_disabled:
            print(f"\n✅ Disabled {len(features_disabled)} features:")
            for feature in features_disabled:
                print(f"   - {feature}")
        else:
            print("ℹ️ All features were already disabled")
            
    except ImportError:
        print("⚠️ Feature flags module not found - may not be installed yet")
    except Exception as e:
        print(f"❌ Error disabling feature flags: {e}")
    
    # Revert database settings to defaults
    print("\nReverting database settings to defaults...")
    
    # Import database configuration
    try:
        from config.database_config import get_database_path, get_environment
        
        # Get database files
        db_files = []
        for env in ['test', 'production']:
            try:
                db_path = str(get_database_path(env))
                if os.path.exists(db_path):
                    db_files.append((env, db_path))
            except:
                pass
    except ImportError:
        # Fallback to known database locations
        db_files = []
        possible_paths = [
            ('production', 'database/league_analytics.db'),
            ('test', 'database/league_analytics_test.db')
        ]
        for env, path in possible_paths:
            if os.path.exists(path):
                db_files.append((env, path))
    
    if not db_files:
        print("⚠️ No database files found to revert")
    else:
        for env, db_file in db_files:
            print(f"\nReverting {env} database: {db_file}")
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Check current settings
                journal_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
                print(f"  Current journal mode: {journal_mode}")
                
                # If in WAL mode, checkpoint and switch back
                if journal_mode.upper() == 'WAL':
                    print("  Checkpointing WAL data...")
                    result = cursor.execute("PRAGMA wal_checkpoint(FULL)").fetchone()
                    print(f"  Checkpoint result: {result}")
                    
                    # Switch back to DELETE mode (default)
                    cursor.execute("PRAGMA journal_mode = DELETE")
                    new_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
                    print(f"  Journal mode changed to: {new_mode}")
                
                # Reset other pragmas to defaults
                print("  Resetting PRAGMA settings to defaults...")
                cursor.execute("PRAGMA synchronous = FULL")     # Default safety
                cursor.execute("PRAGMA busy_timeout = 0")       # Default no timeout
                cursor.execute("PRAGMA cache_size = -2000")     # Default 2MB cache
                cursor.execute("PRAGMA temp_store = DEFAULT")   # Default temp storage
                
                # Verify changes
                settings = {
                    'synchronous': cursor.execute("PRAGMA synchronous").fetchone()[0],
                    'busy_timeout': cursor.execute("PRAGMA busy_timeout").fetchone()[0],
                    'cache_size': cursor.execute("PRAGMA cache_size").fetchone()[0],
                    'journal_mode': cursor.execute("PRAGMA journal_mode").fetchone()[0]
                }
                
                conn.close()
                
                print(f"  ✅ {env} database reverted to defaults")
                print(f"     Settings: {settings}")
                
                # Clean up WAL files if they exist
                for ext in ['-wal', '-shm']:
                    wal_file = db_file + ext
                    if os.path.exists(wal_file):
                        try:
                            os.remove(wal_file)
                            print(f"  Removed {ext} file")
                        except Exception as e:
                            print(f"  Warning: Could not remove {ext} file: {e}")
                
            except Exception as e:
                print(f"  ❌ Error reverting {env} database: {e}")
    
    # Create rollback log
    print("\nCreating rollback log...")
    
    rollback_log = {
        'timestamp': datetime.now().isoformat(),
        'action': 'emergency_rollback',
        'databases_reverted': [env for env, _ in db_files],
        'features_disabled': features_disabled if 'features_disabled' in locals() else [],
        'reason': None
    }
    
    # Ask for reason
    print("\nPlease provide a reason for this rollback:")
    print("(Press Enter to skip)")
    reason = input("> ").strip()
    if reason:
        rollback_log['reason'] = reason
    
    # Save rollback log
    log_dir = os.path.dirname(__file__)
    log_file = os.path.join(log_dir, f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    try:
        with open(log_file, 'w') as f:
            json.dump(rollback_log, f, indent=2)
        print(f"\n📄 Rollback log saved to: {log_file}")
    except Exception as e:
        print(f"⚠️ Could not save rollback log: {e}")
        print(f"Log content: {json.dumps(rollback_log, indent=2)}")
    
    print("\n" + "="*50)
    print("✅ EMERGENCY ROLLBACK COMPLETE")
    print("="*50)
    
    print("\n🔍 Next steps:")
    print("1. Monitor application for stability")
    print("2. Check application logs for errors")
    print("3. Review rollback log for details")
    print("4. Investigate root cause of issues")
    print("5. Plan corrective actions before re-enabling features")
    
    print("\n📝 To re-enable features gradually:")
    print("   python database/manage_features.py --enable pragma_optimizations")
    print("   python database/manage_features.py --status")
    
    return rollback_log


def verify_rollback():
    """
    Verify that rollback was successful.
    """
    print("\n" + "="*50)
    print("ROLLBACK VERIFICATION")
    print("="*50)
    
    all_good = True
    
    # Check feature flags
    try:
        from database.feature_flags import DatabaseFeatureFlags
        flags = DatabaseFeatureFlags()
        
        enabled_features = [f for f, enabled in flags.flags.items() if enabled]
        
        if enabled_features:
            print(f"⚠️ Warning: Some features are still enabled: {enabled_features}")
            all_good = False
        else:
            print("✅ All feature flags are disabled")
    except ImportError:
        print("ℹ️ Feature flags module not available")
    
    # Check database settings
    try:
        from config.database_config import get_database_path, get_environment
        
        for env in ['test', 'production']:
            try:
                db_path = str(get_database_path(env))
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    journal_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
                    busy_timeout = cursor.execute("PRAGMA busy_timeout").fetchone()[0]
                    
                    if journal_mode.upper() == 'WAL':
                        print(f"⚠️ {env} database still in WAL mode")
                        all_good = False
                    elif busy_timeout > 0:
                        print(f"ℹ️ {env} database has busy_timeout={busy_timeout}")
                    else:
                        print(f"✅ {env} database using default settings")
                    
                    conn.close()
            except Exception as e:
                print(f"⚠️ Could not check {env} database: {e}")
    except ImportError:
        print("ℹ️ Database config module not available")
    
    if all_good:
        print("\n✅ Rollback verification passed - all systems at defaults")
    else:
        print("\n⚠️ Some issues detected - manual intervention may be required")
    
    return all_good


if __name__ == "__main__":
    print("SQLite Database Optimization - Emergency Rollback Tool")
    print("="*50)
    
    # Check if user wants to verify only
    if '--verify' in sys.argv:
        verify_rollback()
        sys.exit(0)
    
    # Confirm rollback
    print("\n⚠️ WARNING: This will disable ALL database optimizations")
    print("and revert to default SQLite settings.")
    print("\nThis action is recommended only if you are experiencing:")
    print("- Database lock errors")
    print("- Data corruption")
    print("- Performance degradation")
    print("- Application instability")
    
    print("\nDo you want to proceed with emergency rollback? (yes/no)")
    response = input("> ").strip().lower()
    
    if response == 'yes':
        rollback_log = rollback_all_features()
        
        # Verify rollback
        print("\nRunning post-rollback verification...")
        verify_rollback()
    else:
        print("\nRollback cancelled.")
        print("\nTo check current status:")
        print("   python database/emergency_rollback.py --verify")