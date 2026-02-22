"""Focus OS — macOS menu bar app (main GUI entry point).

Run with: python -m focus.gui
"""

from datetime import date
from pathlib import Path

import rumps
from dotenv import load_dotenv

load_dotenv()

from focus.config import load_config
from focus.daemon import FocusDaemon


_STATUS_ICONS = {
    "on_task": "✓",
    "off_task": "✗",
    "break": "☕",
    "starting": "…",
    "waiting": "…",
    "running": "●",
    "stopped": "○",
    "unknown": "?",
}


class FocusApp(rumps.App):
    def __init__(self):
        super().__init__("Focus", title="○ Focus", quit_button=None)

        self.config = load_config()
        self.daemon = FocusDaemon(self.config)

        # Menu items
        self._status_item = rumps.MenuItem("Status: Stopped", callback=None)
        self._status_item.set_callback(None)
        self._toggle_item = rumps.MenuItem("Start", callback=self._toggle)
        self._stats_item = rumps.MenuItem("Usage Stats…", callback=self._open_stats)
        self._summary_item = rumps.MenuItem("Daily Summary…", callback=self._open_summary)
        self._edit_item = rumps.MenuItem("Edit Focus Rules…", callback=self._open_editor)
        self._settings_item = rumps.MenuItem("Settings…", callback=self._open_settings)
        self._quit_item = rumps.MenuItem("Quit", callback=self._quit)

        self.menu = [
            self._status_item,
            None,  # separator
            self._toggle_item,
            None,
            self._stats_item,
            self._summary_item,
            self._edit_item,
            self._settings_item,
            None,
            self._quit_item,
        ]

        # Poll timer — updates menu bar every 2 seconds
        self._timer = rumps.Timer(self._poll_status, 2)
        self._timer.start()

        # Auto-start daemon
        self._start_daemon()

    def _start_daemon(self):
        self.daemon.run_async()
        self._toggle_item.title = "Stop"
        self._status_item.title = "Status: Starting…"
        self.title = "… Focus"

    def _stop_daemon(self):
        self.daemon.stop()
        self._toggle_item.title = "Start"
        self._status_item.title = "Status: Stopped"
        self.title = "○ Focus"

    def _toggle(self, _):
        status = self.daemon.get_status()
        if status["running"]:
            self._stop_daemon()
        else:
            # Re-create daemon with fresh config
            self.config = load_config()
            self.daemon = FocusDaemon(self.config)
            self._start_daemon()

    def _poll_status(self, _):
        status = self.daemon.get_status()
        if not status["running"]:
            return

        state = status["status"]
        activity = status["activity"]
        icon = _STATUS_ICONS.get(state, "?")

        self.title = f"{icon} Focus"
        if activity:
            self._status_item.title = f"Status: {icon} {activity}"
        else:
            self._status_item.title = f"Status: {state.replace('_', ' ').title()}"

    def _open_stats(self, _):
        """Open usage stats window in a subprocess."""
        from focus.windows import spawn_stats
        # Save latest data before opening window
        self.daemon.usage_tracker.save()
        usage_file = str(
            Path(self.config.log_dir).expanduser()
            / "usage"
            / f"{date.today().isoformat()}.json"
        )
        spawn_stats(usage_file)

    def _open_summary(self, _):
        """Generate today's summary and open the calendar view."""
        from focus.summary import DailySummary
        from focus.windows import spawn_summary
        # Generate/update today's summary before opening
        self.daemon.usage_tracker.save()
        ds = DailySummary(self.config)
        ds.generate_today()
        base = Path(self.config.log_dir).expanduser()
        spawn_summary(
            str(base / "summaries"),
            str(self.config.log_path),
            str(base / "usage"),
        )

    def _open_editor(self, _):
        """Open prompt editor in a subprocess (pywebview needs main thread)."""
        from focus.windows import spawn_prompt_editor
        spawn_prompt_editor(str(self.config.prompt_path.resolve()))

    def _open_settings(self, _):
        """Open settings window in a subprocess."""
        from focus.windows import spawn_settings
        config_dict = {
            "capture_interval": self.config.capture_interval,
            "analysis_interval": self.config.analysis_interval,
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "notification_style": self.config.notification_style,
            "notification_cooldown": self.config.notification_cooldown,
            "escalation_delay": self.config.escalation_delay,
        }
        spawn_settings(config_dict)

    def _poll_config_reload(self):
        """Reload config from disk (settings subprocess writes directly to config.yaml)."""
        self.config = load_config()
        self.daemon.config = self.config
        self.daemon.notifier.config = self.config

    def _quit(self, _):
        self.daemon.stop()
        rumps.quit_application()


def main():
    FocusApp().run()


if __name__ == "__main__":
    main()
