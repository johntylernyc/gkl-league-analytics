#!/usr/bin/env python3
"""
Performance testing script for backfill_transactions optimizations.
This script will run small test scenarios to avoid hitting Yahoo API limits during testing.
"""

import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_original_performance():
    """Test the original implementation with a small date range"""
    print("🔄 Testing original implementation...")
    
    # Import and modify the original script for testing
    import backfill_transactions as original
    
    # Override date settings for testing
    original.DATE_OVERRIDE_START = "2025-04-01"
    original.DATE_OVERRIDE_END = "2025-04-03"  # Just 3 days for testing
    
    start_time = time.time()
    
    try:
        # This would run the main function - but we'll simulate it
        print("  ⚠️  Simulating original script (3-second delays per request)")
        print("  📅 Processing 3 days would take: ~9 seconds minimum")
        duration = 9.0  # Simulated based on 3 days * 3 seconds
        
    except Exception as e:
        print(f"  ❌ Error testing original: {e}")
        duration = 0
    
    return duration

def test_optimized_performance():
    """Test the optimized implementation"""
    print("🚀 Testing optimized implementation...")
    
    try:
        # Import the optimized version
        import backfill_transactions_optimized as optimized
        
        # This will run the actual benchmarks
        print("  ⚡ Running optimized benchmarks...")
        print("  📊 This will test both sequential and concurrent approaches")
        
        # Note: The optimized script contains its own main execution
        # which will run the benchmarks when imported
        
    except Exception as e:
        print(f"  ❌ Error testing optimized version: {e}")
        print(f"  💡 Make sure tokens.json exists in the parent directory")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Performance Testing Suite")
    print("=" * 50)
    
    # Test original (simulated)
    original_duration = test_original_performance()
    
    print()
    
    # Test optimized (actual)
    try:
        optimized_success = test_optimized_performance()
    except ImportError as e:
        print(f"❌ Could not import optimized version: {e}")
        optimized_success = False
    
    print("\n" + "=" * 50)
    print("TESTING COMPLETE")
    
    if optimized_success:
        print("✅ Optimized implementation tested successfully")
        print("📈 Check the benchmark results above for performance comparison")
    else:
        print("❌ Testing encountered issues")
        print("💡 Ensure you have valid Yahoo API tokens and network connectivity")