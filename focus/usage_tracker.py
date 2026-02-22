"""Track frontmost application usage over time.

Polls the active app via osascript at each capture interval and accumulates
seconds per app. Persists daily totals to a JSON file so stats survive restarts.
"""

import json
import subprocess
import time
from datetime import date, datetime
from pathlib import Path
from threading import Lock

from focus.config import Config


class UsageTracker:
    def __init__(self, config: Config):
        self._config = config
        self._lock = Lock()
        # {app_name: total_seconds} for today
        self._today: dict[str, float] = {}
        self._date: str = _today_str()
        self._last_app: str | None = None
        self._last_poll_time: float | None = None
        self._storage_path = Path(config.log_dir).expanduser() / "usage"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def poll(self):
        """Call on each capture cycle. Detects frontmost app and accumulates time."""
        now = time.time()
        today = _today_str()

        # Day rollover
        if today != self._date:
            self._save()
            with self._lock:
                self._today = {}
                self._date = today
                self._last_app = None
                self._last_poll_time = None

        app = _get_frontmost_app()
        if not app:
            self._last_poll_time = now
            return

        with self._lock:
            if self._last_app and self._last_poll_time is not None:
                elapsed = min(now - self._last_poll_time, 60)  # cap at 60s to handle sleep
                self._today[self._last_app] = self._today.get(self._last_app, 0) + elapsed
            self._last_app = app
            self._last_poll_time = now

        # Persist periodically (every ~30 polls ≈ 5 min at 10s interval)
        if int(now) % 300 < self._config.capture_interval:
            self._save()

    def get_stats(self) -> dict:
        """Return today's usage: {app_name: seconds}, sorted descending."""
        with self._lock:
            # Include time for the currently active app up to now
            snapshot = dict(self._today)
            if self._last_app and self._last_poll_time is not None:
                elapsed = min(time.time() - self._last_poll_time, 60)
                snapshot[self._last_app] = snapshot.get(self._last_app, 0) + elapsed

        return dict(sorted(snapshot.items(), key=lambda x: x[1], reverse=True))

    def save(self):
        """Public save — call on shutdown."""
        self.poll()  # capture final interval
        self._save()

    # ── Persistence ────────────────────────────────────────────────────────

    def _file_for(self, day: str) -> Path:
        return self._storage_path / f"{day}.json"

    def _save(self):
        with self._lock:
            data = {"date": self._date, "apps": dict(self._today)}
        try:
            self._file_for(self._date).write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    def _load(self):
        path = self._file_for(self._date)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            if data.get("date") == self._date:
                with self._lock:
                    self._today = data.get("apps", {})
        except (json.JSONDecodeError, OSError):
            pass


# ── Helpers ────────────────────────────────────────────────────────────────

def _today_str() -> str:
    return date.today().isoformat()


def _get_frontmost_app() -> str | None:
    """Return the name of the frontmost application via osascript."""
    try:
        result = subprocess.run(
            [
                "osascript", "-e",
                'tell application "System Events" to get name of first '
                "application process whose frontmost is true",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
        name = result.stdout.strip()
        return name if name else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return None
