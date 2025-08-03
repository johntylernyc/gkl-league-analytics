"""
Feature flags for gradual database optimization rollout.
"""
import os
import json
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseFeatureFlags:
    """
    Manage feature flags for database optimizations.
    Allows gradual rollout and quick rollback.
    """
    
    DEFAULT_FLAGS = {
        'pragma_optimizations': False,
        'wal_mode': False,
        'explicit_transactions': False,
        'retry_logic': False,
        'connection_pooling': False,
        'aggressive_caching': False,
        'isolation_levels': False
    }
    
    def __init__(self, config_file: str = None):
        if config_file is None:
            # Default to database directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(script_dir, 'feature_flags.json')
        
        self.config_file = config_file
        self.flags = self._load_flags()
        self.start_time = datetime.now()
        
    def _load_flags(self) -> Dict[str, bool]:
        """Load flags from config file or use defaults."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_flags = json.load(f)
                    # Merge with defaults to handle new flags
                    flags = self.DEFAULT_FLAGS.copy()
                    flags.update(loaded_flags)
                    logger.info(f"Loaded feature flags from {self.config_file}")
                    return flags
            except Exception as e:
                logger.error(f"Error loading feature flags: {e}")
        
        logger.info("Using default feature flags (all disabled)")
        return self.DEFAULT_FLAGS.copy()
    
    def save_flags(self):
        """Persist current flag state."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.flags, f, indent=2)
            logger.info(f"Feature flags saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving feature flags: {e}")
    
    def is_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        enabled = self.flags.get(feature, False)
        if enabled:
            logger.debug(f"Feature '{feature}' is ENABLED")
        return enabled
    
    def enable(self, feature: str) -> bool:
        """Enable a feature."""
        if feature in self.flags:
            old_value = self.flags[feature]
            self.flags[feature] = True
            self.save_flags()
            logger.info(f"Feature '{feature}' changed from {old_value} to True")
            return True
        else:
            logger.error(f"Unknown feature: {feature}")
            return False
    
    def disable(self, feature: str) -> bool:
        """Disable a feature."""
        if feature in self.flags:
            old_value = self.flags[feature]
            self.flags[feature] = False
            self.save_flags()
            logger.info(f"Feature '{feature}' changed from {old_value} to False")
            return True
        else:
            logger.error(f"Unknown feature: {feature}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all flags."""
        return {
            'flags': self.flags.copy(),
            'uptime': str(datetime.now() - self.start_time),
            'config_file': self.config_file
        }
    
    def reset_to_defaults(self):
        """Reset all flags to default values."""
        self.flags = self.DEFAULT_FLAGS.copy()
        self.save_flags()
        logger.info("All feature flags reset to defaults (disabled)")

# Global instance - lazy initialization
_global_flags = None

def get_feature_flags() -> DatabaseFeatureFlags:
    """Get the global feature flags instance."""
    global _global_flags
    if _global_flags is None:
        _global_flags = DatabaseFeatureFlags()
    return _global_flags

# Convenience functions
def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled."""
    return get_feature_flags().is_enabled(feature)

def enable_feature(feature: str) -> bool:
    """Enable a feature."""
    return get_feature_flags().enable(feature)

def disable_feature(feature: str) -> bool:
    """Disable a feature."""
    return get_feature_flags().disable(feature)

def get_all_flags() -> Dict[str, bool]:
    """Get all feature flags."""
    return get_feature_flags().flags.copy()