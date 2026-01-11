import os
import sys
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Type, Optional, List
import traceback
from datetime import datetime
import shutil


def traceback_str(e: Exception):
    """Convert exception to string with traceback."""
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))


def write_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("bot_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


@dataclass
class Config:
    interval: int = 5
    # Email notifications
    enable_email: bool = False
    to_email: str = "xxx@gmail.com"
    from_email: str = "xxx@gmail.com"
    email_password: str = "xxxx xxxx xxxx xxxx"
    # AutoHotkey
    enable_autohotkey: bool = False
    spam_key: str = "[+1"
    # ntfy notifications
    enable_ntfy: bool = False
    ntfy_topic: str = "my-alerts"
    ntfy_server: str = "https://ntfy.sh"
    ntfy_priority: int = 3
    ntfy_tags: Optional[List[str]] = None
    ntfy_auth_token: Optional[str] = None


class ConfigManager:
    def __init__(self, config_cls: Type[Config] = Config, filename="config.json"):
        self.filename = filename
        self.config_cls = config_cls
        self.config_path = self._get_config_path()
        self.config: Config = self.config_cls()
        self.load()

    def _get_config_path(self):
        """Determines if the app is running as a script or a frozen executable."""
        if getattr(sys, "frozen", False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent
        return base_path / self.filename

    def load(self):
        """Loads config from disk or initializes with defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.config = self.config_cls(**{k: v for k, v in raw.items()})
                print(f"✓ Configuration loaded from {self.config_path}")
                self.save()
                return self.config
            except Exception as e:
                print(f"⚠ Error loading config: {traceback_str(e)}")
                print("Using default configuration")

        # Fallback to defaults
        self.config = self.config_cls()
        self.save(backup=self.config_path.exists())
        return self.config

    def save(self, backup=False):
        """Saves the current state of self.config to disk."""
        if backup:
            self.backup()
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.config), f, indent=4)
            print(f"✓ Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"✗ Error saving config: {traceback_str(e)}")

    def backup(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.config_path}.{timestamp}.bak"
            shutil.copy2(self.config_path, backup_path)
            print(f"✓ Backup created at {backup_path}")
        except Exception as e:
            print(f"✗ Error backup config: {traceback_str(e)}")
