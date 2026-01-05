import os
import sys
import json
from pathlib import Path
import traceback


def traceback_str(e: Exception):
    """Convert exception to string with traceback."""
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class ConfigManager:
    def __init__(self, filename="config.json", default_config=None):
        self.filename = filename
        self.default_config = default_config or {}
        self.config_path = self._get_config_path()
        self.config = {}
        
        # Load immediately on instantiation
        self.load()

    def _get_config_path(self):
        """Determines if the app is running as a script or a frozen executable."""
        if getattr(sys, 'frozen', False):
            # If running as an .exe (PyInstaller)
            base_path = Path(sys.executable).parent
        else:
            # If running as a .py script
            base_path = Path(__file__).parent
            
        return base_path / self.filename

    def load(self):
        """Loads config from disk or initializes with defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                print(f"✓ Configuration loaded from {self.config_path}")
                return self.config
            except Exception as e:
                print(f"⚠ Error loading config: {traceback_str(e)}")
                print("Using default configuration")
        
        # Fallback to defaults
        self.config = self.default_config.copy()
        self.save()
        return self.config

    def save(self):
        """Saves the current state of self.config to disk."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print(f"✓ Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"✗ Error saving config: {traceback_str(e)}")

    def get(self, key, default=None):
        """Helper to get values without crashing if the key is missing."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Helper to set a value and save automatically."""
        self.config[key] = value
        self.save()

