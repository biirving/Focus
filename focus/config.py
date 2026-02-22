"""Configuration loading for Focus OS."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Config:
    # Intervals
    capture_interval: int = 10  # seconds between screenshots
    analysis_interval: int = 30  # seconds between API calls

    # Claude API
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 512

    # Paths
    prompt_file: str = "prompt.md"
    screenshot_dir: str = "/tmp/focus_screenshots"
    log_dir: str = "~/.focus"
    log_file: str = "activity_log.jsonl"

    # Screenshot
    max_screenshots: int = 10  # rolling buffer size
    resize_max_dimension: int = 1092

    # Notifications
    notification_style: str = "system"  # "system" or "banner"
    notification_cooldown: int = 120  # seconds between notifications
    escalation_delay: int = 120  # seconds before escalating

    # Activity tracking
    history_window: int = 1800  # 30 minutes in seconds
    max_history_entries: int = 60

    # Verbosity
    verbose: bool = False

    @property
    def prompt_path(self) -> Path:
        return Path(self.prompt_file)

    @property
    def screenshot_path(self) -> Path:
        return Path(self.screenshot_dir)

    @property
    def log_path(self) -> Path:
        return Path(self.log_dir).expanduser() / self.log_file


def load_config(config_path: Optional[str] = None) -> Config:
    """Load config from YAML file, falling back to defaults."""
    if config_path is None:
        config_path = "config.yaml"

    path = Path(config_path)
    if not path.exists():
        return Config()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return Config(**{k: v for k, v in data.items() if hasattr(Config, k) and v is not None and v != ""})
