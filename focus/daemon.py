"""Main orchestrator — capture thread + analysis loop."""

import signal
import threading
import time
from pathlib import Path

from focus.activity import ActivityTracker
from focus.analyzer import Analyzer
from focus.capture import ScreenCapture
from focus.config import Config
from focus.notifier import Notifier
from focus.prompt_loader import PromptLoader
from focus.usage_tracker import UsageTracker


class FocusDaemon:
    def __init__(self, config: Config):
        self.config = config
        self.capture = ScreenCapture(config)
        self.analyzer = Analyzer(config)
        self.prompt_loader = PromptLoader(config)
        self.tracker = ActivityTracker(config)
        self.notifier = Notifier(config)
        self.usage_tracker = UsageTracker(config)

        self._running = False
        self._latest_screenshots: list[Path] = []
        self._screenshot_lock = threading.Lock()
        self._daemon_thread: threading.Thread | None = None
        self._latest_status: str = "stopped"
        self._latest_activity: str = ""
        self._status_lock = threading.Lock()

    def run(self):
        """Start the daemon: capture thread + analysis loop on main thread."""
        self._running = True

        # Handle SIGTERM gracefully
        signal.signal(signal.SIGTERM, lambda *_: self.stop())

        print("Focus OS started")
        print(f"  Model: {self.config.model}")
        print(f"  Capture: every {self.config.capture_interval}s")
        print(f"  Analysis: every {self.config.analysis_interval}s")
        print(f"  Prompt: {self.config.prompt_path}")
        print(f"  Screenshots: {self.config.screenshot_path}")
        print(f"  Log: {self.config.log_path}")
        print()

        self._run_main_loop()

    def run_async(self):
        """Start the daemon in a background thread and return immediately."""
        if self._daemon_thread is not None and self._daemon_thread.is_alive():
            return

        self._running = True
        self._daemon_thread = threading.Thread(target=self._run_main_loop, daemon=True)
        self._daemon_thread.start()
        with self._status_lock:
            self._latest_status = "starting"

    def stop(self):
        """Stop the daemon gracefully."""
        self._running = False
        self.capture.cleanup()
        self.usage_tracker.save()
        with self._status_lock:
            self._latest_status = "stopped"
            self._latest_activity = ""
        print("Focus OS stopped")

    def get_status(self) -> dict:
        """Return current daemon state for GUI polling."""
        with self._status_lock:
            return {
                "running": self._running,
                "status": self._latest_status,
                "activity": self._latest_activity,
            }

    def _run_main_loop(self):
        """Core loop: start capture thread, then run analysis loop."""
        # Start capture thread
        capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        capture_thread.start()

        # Run analysis loop
        self._analysis_loop()

    def _capture_loop(self):
        """Background thread: capture screenshots at regular intervals."""
        while self._running:
            paths = self.capture.capture()
            if paths:
                with self._screenshot_lock:
                    self._latest_screenshots = paths
            self.usage_tracker.poll()
            time.sleep(self.config.capture_interval)

    def _analysis_loop(self):
        """Main thread: analyze screenshots at regular intervals."""
        # Wait for first screenshot
        with self._status_lock:
            self._latest_status = "waiting"
        print("Waiting for first screenshot...")
        while self._running:
            with self._screenshot_lock:
                if self._latest_screenshots:
                    break
            time.sleep(1)

        if not self._running:
            return

        with self._status_lock:
            self._latest_status = "running"
        print("Monitoring active.\n")

        while self._running:
            self._run_analysis_cycle()
            # Sleep in small increments so we can stop quickly
            for _ in range(self.config.analysis_interval):
                if not self._running:
                    return
                time.sleep(1)

    def _run_analysis_cycle(self):
        """Run one analysis cycle: grab screenshot, analyze, notify."""
        # Hot-reload prompt if changed
        self.prompt_loader.reload_if_changed()

        # Grab latest screenshots
        with self._screenshot_lock:
            screenshots = list(self._latest_screenshots)

        if not screenshots:
            if self.config.verbose:
                print("  [daemon] no screenshot available")
            return

        # Analyze
        result = self.analyzer.analyze(
            screenshot_path=screenshots,
            prompt_content=self.prompt_loader.content,
            activity_history=self.tracker.format_history(),
        )

        if result is None:
            return

        # Record activity
        self.tracker.record(result)

        # Update status for GUI
        with self._status_lock:
            self._latest_status = result.status.value
            self._latest_activity = result.activity_description

        # Check time budgets
        exceeded = self.tracker.check_budgets(self.prompt_loader.budgets)
        if exceeded and self.config.verbose:
            for msg in exceeded:
                print(f"  [budget] exceeded: {msg}")

        # Status line (always printed)
        status_icon = {
            "on_task": "✓",
            "off_task": "✗",
            "break": "☕",
            "unknown": "?",
        }.get(result.status.value, "?")
        ts = result.timestamp.strftime("%H:%M:%S")
        print(f"[{ts}] {status_icon} {result.activity_description}")

        # Notify if off-task
        off_task_duration = self.tracker.get_off_task_duration()
        self.notifier.notify_if_needed(result, off_task_duration)
