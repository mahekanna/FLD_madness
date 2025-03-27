"""
Configuration management for the Fibonacci Cycle Trading System
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages application configuration settings with disk persistence
    """
    
    def __init__(self, config_file="./config/settings.json"):
        """
        Initialize the configuration manager
        
        Args:
            config_file: Path to JSON configuration file
        """
        self.config_file = config_file
        self.config = {}
        self.defaults = {}
        
        # Create default configuration
        self._set_defaults()
        
        # Load configuration from file
        self._ensure_config_dir()
        self.load_config()
    
    def _set_defaults(self):
        """Set default configuration values"""
        self.defaults = {
            "general": {
                "default_exchange": "NSE",
                "default_interval": "daily",
                "default_lookback": 5000,
                "symbols_file_path": "./data/symbols/default_symbols.csv",
                "report_dir": "./data/reports",
                "data_dir": "./data",
                "cache_dir": "./data/cache",
                "cache_expiry": 86400  # 24 hours in seconds
            },
            "analysis": {
                "cycle_detection_method": "fft",
                "min_period": 20,
                "max_period": 250,
                "num_cycles": 3,
                "fib_cycles": [20, 21, 34, 55, 89],
                "signal_threshold": 1.0
            },
            "performance": {
                "use_gpu": False,
                "max_workers": 5,
                "batch_size": 20
            },
            "visualization": {
                "chart_height": 600,
                "show_volume": True,
                "show_crossings": True,
                "max_bars": 500
            },
            "notifications": {
                "telegram_enabled": False,
                "telegram_token": "",
                "telegram_chat_id": "",
                "notification_options": []
            },
            "backtest": {
                "default_strategy": "fld_crossover",
                "default_stop_loss": "atr",
                "default_take_profit": "next_cycle",
                "default_position_sizing": "risk_based",
                "default_risk_percentage": 2.0
            }
        }
        
        # Initialize config with defaults
        self.config = self.defaults.copy()
    
    def _ensure_config_dir(self):
        """Ensure the configuration directory exists"""
        config_dir = os.path.dirname(self.config_file)
        if config_dir and not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
                logger.info(f"Created configuration directory: {config_dir}")
            except Exception as e:
                logger.error(f"Failed to create configuration directory: {e}")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with defaults
                self._merge_configs(self.config, loaded_config)
                logger.info(f"Configuration loaded from {self.config_file}")
                return True
            else:
                logger.info(f"Configuration file {self.config_file} not found, using defaults")
                # Save defaults to file
                self.save_config()
                return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def save_config(self):
        """Save configuration to file"""
        try:
            # Create directory if it doesn't exist
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, section, key=None, default=None):
        """
        Get a configuration value
        
        Args:
            section: Configuration section
            key: Configuration key (optional, if None, returns entire section)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            if section not in self.config:
                # Return section default if available
                if section in self.defaults:
                    if key is None:
                        return self.defaults[section]
                    elif key in self.defaults[section]:
                        return self.defaults[section][key]
                return default
            
            if key is None:
                # Return entire section
                return self.config[section]
            
            if key in self.config[section]:
                return self.config[section][key]
            
            # Check defaults
            if section in self.defaults and key in self.defaults[section]:
                return self.defaults[section][key]
            
            return default
        except Exception as e:
            logger.error(f"Error getting configuration {section}.{key}: {e}")
            return default
    
    def set(self, section, key, value):
        """
        Set a configuration value
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
            
        Returns:
            True on success, False on failure
        """
        try:
            # Ensure section exists
            if section not in self.config:
                self.config[section] = {}
            
            # Set value
            self.config[section][key] = value
            
            # Save to file
            self.save_config()
            
            return True
        except Exception as e:
            logger.error(f"Error setting configuration {section}.{key}: {e}")
            return False
    
    def update_section(self, section, values):
        """
        Update an entire configuration section
        
        Args:
            section: Configuration section
            values: Dictionary of values to update
            
        Returns:
            True on success, False on failure
        """
        try:
            # Ensure section exists
            if section not in self.config:
                self.config[section] = {}
            
            # Update section
            self.config[section].update(values)
            
            # Save to file
            self.save_config()
            
            return True
        except Exception as e:
            logger.error(f"Error updating configuration section {section}: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = self.defaults.copy()
        self.save_config()
        logger.info("Configuration reset to defaults")
        return True
    
    def _merge_configs(self, target, source):
        """
        Recursively merge source into target
        
        Args:
            target: Target dictionary
            source: Source dictionary
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_configs(target[key], value)
            else:
                target[key] = value

# Create global instance
config = ConfigManager()