"""
Change tracking utilities for detecting data modifications.
Provides consistent hash generation for lineups, stats, and transactions.
"""

import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class ChangeTracker:
    """Utilities for tracking changes in fantasy baseball data."""
    
    @staticmethod
    def normalize_data(data: Any) -> Any:
        """
        Normalize data for consistent hashing.
        Handles various data types and ensures deterministic output.
        
        Args:
            data: Data to normalize (dict, list, or primitive)
            
        Returns:
            Normalized data structure
        """
        if isinstance(data, dict):
            # Sort dictionary keys and recursively normalize values
            return {k: ChangeTracker.normalize_data(v) 
                   for k, v in sorted(data.items())}
        elif isinstance(data, list):
            # Sort lists of dictionaries by a key if available
            if data and isinstance(data[0], dict):
                # Try to sort by common keys
                sort_keys = ['player_id', 'date', 'transaction_id', 'id']
                for key in sort_keys:
                    if key in data[0]:
                        return sorted([ChangeTracker.normalize_data(item) 
                                     for item in data], 
                                    key=lambda x: str(x.get(key, '')))
            # Otherwise return normalized items in original order
            return [ChangeTracker.normalize_data(item) for item in data]
        elif isinstance(data, (int, float)):
            # Round floats to avoid precision issues
            if isinstance(data, float):
                return round(data, 6)
            return data
        elif data is None:
            return None
        else:
            # Convert to string for other types
            return str(data)
    
    @staticmethod
    def generate_hash(data: Dict[str, Any]) -> str:
        """
        Generate a SHA256 hash for any data structure.
        
        Args:
            data: Dictionary containing data to hash
            
        Returns:
            SHA256 hash string
        """
        normalized = ChangeTracker.normalize_data(data)
        data_str = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    @staticmethod
    def generate_lineup_hash(lineup_data: Dict[str, Any]) -> str:
        """
        Generate a deterministic hash for lineup data.
        
        Args:
            lineup_data: Dictionary containing lineup information
                Expected structure:
                {
                    'date': 'YYYY-MM-DD',
                    'team_key': 'team_key',
                    'players': [
                        {'player_id': 123, 'selected_position': 'SS', ...},
                        ...
                    ]
                }
        
        Returns:
            SHA256 hash of the normalized lineup data
        """
        # Extract only the fields that matter for change detection
        normalized = {
            'date': lineup_data.get('date'),
            'team_key': lineup_data.get('team_key'),
            'players': sorted([
                {
                    'player_id': p.get('player_id'),
                    'position': p.get('selected_position'),
                    'status': p.get('status', 'active')
                }
                for p in lineup_data.get('players', [])
            ], key=lambda x: str(x.get('player_id', '')))
        }
        
        return ChangeTracker.generate_hash(normalized)
    
    @staticmethod
    def generate_stats_hash(stats_data: Dict[str, Any]) -> str:
        """
        Generate a deterministic hash for player stats.
        
        Args:
            stats_data: Dictionary containing player statistics
                Expected structure:
                {
                    'player_id': 123,
                    'date': 'YYYY-MM-DD',
                    'stats': {'hits': 2, 'runs': 1, ...}
                }
        
        Returns:
            SHA256 hash of the normalized stats data
        """
        # Normalize stats for consistent hashing
        normalized = {
            'player_id': stats_data.get('player_id'),
            'date': stats_data.get('date'),
            'stats': {k: v for k, v in sorted(stats_data.get('stats', {}).items())}
        }
        
        return ChangeTracker.generate_hash(normalized)
    
    @staticmethod
    def generate_transaction_hash(transaction_data: Dict[str, Any]) -> str:
        """
        Generate a deterministic hash for transaction data.
        
        Args:
            transaction_data: Dictionary containing transaction information
                Expected structure:
                {
                    'transaction_id': 'xxx',
                    'type': 'add',
                    'player_id': 123,
                    'team_key': 'xxx',
                    'date': 'YYYY-MM-DD',
                    'status': 'completed'
                }
        
        Returns:
            SHA256 hash of the normalized transaction data
        """
        # Extract fields that indicate actual changes
        normalized = {
            'transaction_id': transaction_data.get('transaction_id'),
            'type': transaction_data.get('type'),
            'player_id': transaction_data.get('player_id'),
            'team_key': transaction_data.get('team_key'),
            'date': transaction_data.get('date'),
            'status': transaction_data.get('status', 'completed')
        }
        
        return ChangeTracker.generate_hash(normalized)
    
    @staticmethod
    def detect_changes(
        existing_hash: Optional[str], 
        new_data: Dict[str, Any], 
        hash_func: callable
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Detect if data has changed based on content hash.
        
        Args:
            existing_hash: Previously stored hash (None if no existing data)
            new_data: Newly fetched data
            hash_func: Function to generate hash from data
        
        Returns:
            Tuple of (has_changed, new_hash, change_details)
        """
        new_hash = hash_func(new_data)
        
        if existing_hash is None:
            # New data
            return True, new_hash, {'change_type': 'new'}
        elif existing_hash != new_hash:
            # Data has changed
            return True, new_hash, {'change_type': 'modified'}
        else:
            # No changes
            return False, new_hash, None
    
    @staticmethod
    def compare_lineups(
        old_lineup: Dict[str, Any], 
        new_lineup: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two lineups and return detailed change information.
        
        Args:
            old_lineup: Previous lineup data
            new_lineup: New lineup data
        
        Returns:
            Dictionary with change details
        """
        old_players = {p['player_id']: p for p in old_lineup.get('players', [])}
        new_players = {p['player_id']: p for p in new_lineup.get('players', [])}
        
        old_ids = set(old_players.keys())
        new_ids = set(new_players.keys())
        
        changes = {
            'players_added': list(new_ids - old_ids),
            'players_removed': list(old_ids - new_ids),
            'position_changes': {}
        }
        
        # Check for position changes
        for player_id in old_ids & new_ids:
            old_pos = old_players[player_id].get('selected_position')
            new_pos = new_players[player_id].get('selected_position')
            if old_pos != new_pos:
                changes['position_changes'][player_id] = {
                    'from': old_pos,
                    'to': new_pos
                }
        
        return changes
    
    @staticmethod
    def compare_stats(
        old_stats: Dict[str, Any], 
        new_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two stat lines and return corrections.
        
        Args:
            old_stats: Previous stats data
            new_stats: New stats data
        
        Returns:
            Dictionary with stat corrections
        """
        corrections = {}
        
        old_values = old_stats.get('stats', {})
        new_values = new_stats.get('stats', {})
        
        all_keys = set(old_values.keys()) | set(new_values.keys())
        
        for key in all_keys:
            old_val = old_values.get(key, 0)
            new_val = new_values.get(key, 0)
            
            if old_val != new_val:
                corrections[key] = {
                    'old': old_val,
                    'new': new_val,
                    'difference': new_val - old_val if isinstance(new_val, (int, float)) else None
                }
        
        return corrections


class RefreshStrategy:
    """Determines when data should be refreshed based on age and type."""
    
    # Refresh windows in days
    FORCE_REFRESH_DAYS = 3  # Always refresh recent data
    STAT_CORRECTION_WINDOW = 7  # Check for stat corrections
    ARCHIVE_THRESHOLD = 30  # Data older than this is rarely changed
    
    @staticmethod
    def should_refresh(
        data_date: str,
        data_type: str = 'lineup',
        last_fetched: Optional[datetime] = None,
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Determine if data should be refreshed.
        
        Args:
            data_date: Date of the data (YYYY-MM-DD)
            data_type: Type of data ('lineup', 'stats', 'transaction')
            last_fetched: When data was last fetched
            force: Force refresh regardless of age
        
        Returns:
            Tuple of (should_refresh, reason)
        """
        if force:
            return True, "force_refresh"
        
        # Parse the data date
        data_datetime = datetime.strptime(data_date, '%Y-%m-%d')
        now = datetime.now()
        days_old = (now - data_datetime).days
        
        # Check if data doesn't exist
        if last_fetched is None:
            return True, "new_data"
        
        # Force refresh window for recent data
        if days_old <= RefreshStrategy.FORCE_REFRESH_DAYS:
            return True, "recent_data"
        
        # Check for stat corrections (MLB stats only)
        if data_type == 'stats' and days_old <= RefreshStrategy.STAT_CORRECTION_WINDOW:
            # Refresh if last fetched was more than 24 hours ago
            hours_since_fetch = (now - last_fetched).total_seconds() / 3600
            if hours_since_fetch >= 24:
                return True, "stat_correction_window"
        
        # Check if fetched before last scheduled update
        last_scheduled = RefreshStrategy.get_last_scheduled_update()
        if last_fetched < last_scheduled:
            return True, "stale_data"
        
        # Archive data rarely changes
        if days_old > RefreshStrategy.ARCHIVE_THRESHOLD:
            return False, "archive_data"
        
        return False, "up_to_date"
    
    @staticmethod
    def get_last_scheduled_update() -> datetime:
        """
        Get the timestamp of the most recent scheduled update.
        Updates occur at 6AM, 1PM, and 10PM ET.
        
        Returns:
            Datetime of the last scheduled update
        """
        now = datetime.now()
        update_hours = [6, 13, 22]  # 6AM, 1PM, 10PM ET
        
        # Find the most recent past update time today
        for hour in reversed(update_hours):
            update_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if update_time <= now:
                return update_time
        
        # If none today (very early morning), use yesterday's last update
        yesterday = now.replace(hour=22, minute=0, second=0, microsecond=0)
        yesterday = yesterday.replace(day=yesterday.day - 1)
        return yesterday


# Example usage and testing
if __name__ == "__main__":
    # Test lineup hash generation
    lineup = {
        'date': '2025-08-04',
        'team_key': 'mlb.l.6966.t.1',
        'players': [
            {'player_id': 12345, 'selected_position': 'SS', 'status': 'active'},
            {'player_id': 67890, 'selected_position': '1B', 'status': 'active'}
        ]
    }
    
    tracker = ChangeTracker()
    lineup_hash = tracker.generate_lineup_hash(lineup)
    print(f"Lineup hash: {lineup_hash}")
    
    # Test change detection
    existing_hash = None
    has_changed, new_hash, details = tracker.detect_changes(
        existing_hash, lineup, tracker.generate_lineup_hash
    )
    print(f"Has changed: {has_changed}, Details: {details}")
    
    # Test refresh strategy
    strategy = RefreshStrategy()
    should_refresh, reason = strategy.should_refresh('2025-08-03', 'lineup')
    print(f"Should refresh: {should_refresh}, Reason: {reason}")