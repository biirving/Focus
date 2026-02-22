"""Load and hot-reload prompt.md, extract time budgets."""

import os
import re
from pathlib import Path

from focus.config import Config
from focus.models import TimeBudget

# Matches patterns like "(max 15 min per hour)" or "(max 10 min)"
TIME_BUDGET_RE = re.compile(
    r"^[-*]\s+(.+?)\s*\(max\s+(\d+)\s+min(?:\s+per\s+(\d+)\s*(?:min(?:utes?)?|hr|hour))?\)",
    re.MULTILINE | re.IGNORECASE,
)


class PromptLoader:
    def __init__(self, config: Config):
        self.config = config
        self.path = config.prompt_path
        self._content: str = ""
        self._mtime: float = 0
        self._budgets: list[TimeBudget] = []
        self._load()

    def _load(self):
        """Read prompt.md from disk."""
        if not self.path.exists():
            self._content = "No focus rules defined. Monitor all activity."
            self._budgets = []
            return

        self._mtime = os.path.getmtime(self.path)
        self._content = self.path.read_text()
        self._budgets = self._extract_budgets(self._content)

        if self.config.verbose:
            print(f"  [prompt] loaded {self.path} ({len(self._budgets)} time budgets)")

    def _extract_budgets(self, content: str) -> list[TimeBudget]:
        """Extract time budget rules from prompt text."""
        budgets = []
        for match in TIME_BUDGET_RE.finditer(content):
            activity = match.group(1).strip()
            max_minutes = int(match.group(2))
            per_minutes = int(match.group(3)) if match.group(3) else 60
            budgets.append(TimeBudget(
                activity_pattern=activity,
                max_minutes=max_minutes,
                per_minutes=per_minutes,
            ))
        return budgets

    def reload_if_changed(self) -> bool:
        """Check if prompt.md was modified and reload if so. Returns True if reloaded."""
        if not self.path.exists():
            return False
        try:
            current_mtime = os.path.getmtime(self.path)
        except OSError:
            return False

        if current_mtime > self._mtime:
            self._load()
            if self.config.verbose:
                print("  [prompt] reloaded (file changed)")
            return True
        return False

    @property
    def content(self) -> str:
        return self._content

    @property
    def budgets(self) -> list[TimeBudget]:
        return self._budgets
