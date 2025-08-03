#!/usr/bin/env python
"""
Feature flag management utility for database optimizations.
"""
import sys
import os
import argparse
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.feature_flags import DatabaseFeatureFlags


def list_features(flags: DatabaseFeatureFlags):
    """List all available features and their status."""
    print("\n" + "="*50)
    print("DATABASE OPTIMIZATION FEATURES")
    print("="*50)
    
    status = flags.get_status()
    print(f"\nConfig file: {status['config_file']}")
    print(f"Uptime: {status['uptime']}")
    
    print("\nFeature Status:")
    print("-" * 40)
    
    for feature, enabled in sorted(status['flags'].items()):
        icon = "✅" if enabled else "❌"
        print(f"  {icon} {feature:25} {'ENABLED' if enabled else 'DISABLED'}")
    
    # Count enabled features
    enabled_count = sum(1 for enabled in status['flags'].values() if enabled)
    total_count = len(status['flags'])
    
    print(f"\nEnabled: {enabled_count}/{total_count} features")


def enable_feature(flags: DatabaseFeatureFlags, feature: str):
    """Enable a specific feature."""
    if feature == 'all':
        print("⚠️ Enabling ALL features - this is not recommended for production!")
        print("It's safer to enable features gradually.")
        response = input("Are you sure? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Cancelled.")
            return
        
        for f in flags.flags:
            if not flags.flags[f]:
                flags.enable(f)
                print(f"  Enabled: {f}")
        print("\n✅ All features enabled")
    else:
        if flags.enable(feature):
            print(f"✅ Enabled: {feature}")
        else:
            print(f"❌ Unknown feature: {feature}")
            print("\nAvailable features:")
            for f in flags.flags:
                print(f"  - {f}")


def disable_feature(flags: DatabaseFeatureFlags, feature: str):
    """Disable a specific feature."""
    if feature == 'all':
        for f in flags.flags:
            if flags.flags[f]:
                flags.disable(f)
                print(f"  Disabled: {f}")
        print("\n✅ All features disabled")
    else:
        if flags.disable(feature):
            print(f"✅ Disabled: {feature}")
        else:
            print(f"❌ Unknown feature: {feature}")


def apply_profile(flags: DatabaseFeatureFlags, profile: str):
    """Apply a predefined feature profile."""
    profiles = {
        'safe': {
            'pragma_optimizations': True,
            'wal_mode': False,
            'explicit_transactions': False,
            'retry_logic': False,
            'connection_pooling': False,
            'aggressive_caching': False,
            'isolation_levels': False
        },
        'balanced': {
            'pragma_optimizations': True,
            'wal_mode': True,
            'explicit_transactions': True,
            'retry_logic': True,
            'connection_pooling': False,
            'aggressive_caching': False,
            'isolation_levels': False
        },
        'performance': {
            'pragma_optimizations': True,
            'wal_mode': True,
            'explicit_transactions': True,
            'retry_logic': True,
            'connection_pooling': True,
            'aggressive_caching': True,
            'isolation_levels': True
        },
        'test': {
            'pragma_optimizations': True,
            'wal_mode': False,  # May not work on all test systems
            'explicit_transactions': True,
            'retry_logic': True,
            'connection_pooling': False,
            'aggressive_caching': False,
            'isolation_levels': False
        }
    }
    
    if profile not in profiles:
        print(f"❌ Unknown profile: {profile}")
        print("\nAvailable profiles:")
        for p, settings in profiles.items():
            enabled = sum(1 for v in settings.values() if v)
            print(f"  - {p:12} ({enabled} features enabled)")
        return
    
    print(f"\nApplying profile: {profile}")
    print("-" * 40)
    
    settings = profiles[profile]
    for feature, should_enable in settings.items():
        current = flags.flags.get(feature, False)
        if should_enable != current:
            if should_enable:
                flags.enable(feature)
                print(f"  Enabled: {feature}")
            else:
                flags.disable(feature)
                print(f"  Disabled: {feature}")
    
    print(f"\n✅ Profile '{profile}' applied")


def show_recommendations():
    """Show feature recommendations based on use case."""
    print("\n" + "="*50)
    print("FEATURE RECOMMENDATIONS")
    print("="*50)
    
    recommendations = [
        {
            'scenario': 'Initial Testing',
            'profile': 'safe',
            'features': ['pragma_optimizations'],
            'description': 'Start with basic PRAGMA settings only'
        },
        {
            'scenario': 'Development Environment',
            'profile': 'test',
            'features': ['pragma_optimizations', 'explicit_transactions', 'retry_logic'],
            'description': 'Good balance for development without WAL complexity'
        },
        {
            'scenario': 'Production - Conservative',
            'profile': 'balanced',
            'features': ['pragma_optimizations', 'wal_mode', 'explicit_transactions', 'retry_logic'],
            'description': 'Recommended for production with good stability'
        },
        {
            'scenario': 'Production - Performance',
            'profile': 'performance',
            'features': ['all'],
            'description': 'Maximum performance (test thoroughly first!)'
        }
    ]
    
    for rec in recommendations:
        print(f"\n{rec['scenario']}:")
        print(f"  Profile: {rec['profile']}")
        print(f"  Features: {', '.join(rec['features'])}")
        print(f"  {rec['description']}")
    
    print("\n" + "="*50)
    print("DEPLOYMENT SEQUENCE")
    print("="*50)
    
    print("""
Recommended gradual deployment over 2 weeks:

Day 1-2:   Enable 'pragma_optimizations'
           Monitor for issues

Day 3-4:   Enable 'explicit_transactions'
           Check transaction success rates

Day 5-6:   Enable 'wal_mode' (after compatibility check)
           Monitor WAL file growth

Day 7-8:   Enable 'retry_logic'
           Check retry frequencies

Day 9-10:  Enable 'connection_pooling' (if needed)
           Monitor connection usage

Day 11-12: Enable 'aggressive_caching' (optional)
           Check memory usage

Day 13-14: Enable 'isolation_levels' (if needed)
           Final validation
""")


def export_config(flags: DatabaseFeatureFlags, output_file: str):
    """Export current configuration."""
    config = {
        'exported_at': datetime.now().isoformat(),
        'flags': flags.flags,
        'config_file': flags.config_file
    }
    
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration exported to: {output_file}")


def import_config(flags: DatabaseFeatureFlags, input_file: str):
    """Import configuration from file."""
    try:
        with open(input_file, 'r') as f:
            config = json.load(f)
        
        if 'flags' not in config:
            print("❌ Invalid configuration file")
            return
        
        print(f"Importing configuration from: {input_file}")
        print(f"Exported at: {config.get('exported_at', 'Unknown')}")
        
        for feature, enabled in config['flags'].items():
            if feature in flags.flags:
                flags.flags[feature] = enabled
                print(f"  Set {feature}: {enabled}")
        
        flags.save_flags()
        print("✅ Configuration imported")
        
    except Exception as e:
        print(f"❌ Error importing configuration: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Manage database optimization feature flags',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_features.py --status                    # Show current status
  python manage_features.py --enable pragma_optimizations  # Enable a feature
  python manage_features.py --disable all               # Disable all features
  python manage_features.py --profile balanced          # Apply a profile
  python manage_features.py --recommendations           # Show recommendations
"""
    )
    
    parser.add_argument('--status', '-s', action='store_true',
                       help='Show current feature status')
    parser.add_argument('--enable', '-e', metavar='FEATURE',
                       help='Enable a feature (or "all")')
    parser.add_argument('--disable', '-d', metavar='FEATURE',
                       help='Disable a feature (or "all")')
    parser.add_argument('--profile', '-p', choices=['safe', 'balanced', 'performance', 'test'],
                       help='Apply a predefined profile')
    parser.add_argument('--recommendations', '-r', action='store_true',
                       help='Show feature recommendations')
    parser.add_argument('--export', metavar='FILE',
                       help='Export configuration to file')
    parser.add_argument('--import', metavar='FILE', dest='import_file',
                       help='Import configuration from file')
    parser.add_argument('--reset', action='store_true',
                       help='Reset all features to defaults (disabled)')
    
    args = parser.parse_args()
    
    # Initialize feature flags
    flags = DatabaseFeatureFlags()
    
    # Handle commands
    if args.reset:
        flags.reset_to_defaults()
        print("✅ All features reset to defaults (disabled)")
    elif args.enable:
        enable_feature(flags, args.enable)
    elif args.disable:
        disable_feature(flags, args.disable)
    elif args.profile:
        apply_profile(flags, args.profile)
    elif args.recommendations:
        show_recommendations()
    elif args.export:
        export_config(flags, args.export)
    elif args.import_file:
        import_config(flags, args.import_file)
    else:
        # Default to showing status
        list_features(flags)
        
        if not any(flags.flags.values()):
            print("\n💡 Tip: Use --recommendations to see deployment suggestions")
            print("        Use --enable <feature> to enable specific features")
            print("        Use --profile <name> to apply a feature set")


if __name__ == "__main__":
    main()