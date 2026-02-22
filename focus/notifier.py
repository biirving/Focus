"""macOS notifications via osascript or banner overlay."""

import subprocess
import time
from pathlib import Path

from focus.config import Config
from focus.models import AnalysisResult, FocusStatus

# Paths for the Swift banner
_BANNER_SWIFT = Path(__file__).parent / "banner.swift"
_BANNER_BIN = Path(__file__).parent / "banner_bin"


def _ensure_banner_compiled() -> Path | None:
    """Compile banner.swift to a binary on first use. Returns binary path or None."""
    if _BANNER_BIN.exists():
        return _BANNER_BIN
    if not _BANNER_SWIFT.exists():
        return None
    try:
        subprocess.run(
            ["swiftc", "-O", str(_BANNER_SWIFT), "-o", str(_BANNER_BIN)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return _BANNER_BIN
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None


class Notifier:
    def __init__(self, config: Config):
        self.config = config
        self._last_notification_time: float = 0
        self._escalation_start: float | None = None
        self._banner_bin: Path | None = None
        self._banner_procs: list[subprocess.Popen] = []

    def notify_if_needed(self, result: AnalysisResult, off_task_duration: float):
        """Send a notification if the user is off-task and cooldown has elapsed."""
        now = time.time()

        if result.status != FocusStatus.OFF_TASK:
            # Reset escalation when back on task
            if self._escalation_start is not None:
                self._escalation_start = None
                if self.config.verbose:
                    print("  [notifier] escalation reset (back on task)")
            return

        # Check cooldown
        time_since_last = now - self._last_notification_time
        if time_since_last < self.config.notification_cooldown:
            return

        # Determine escalation level
        if self._escalation_start is None:
            self._escalation_start = now

        escalation_time = now - self._escalation_start
        is_escalated = escalation_time >= self.config.escalation_delay

        if is_escalated:
            self._send_urgent(result, off_task_duration)
        else:
            self._send_gentle(result)

        self._last_notification_time = now

    def _send_gentle(self, result: AnalysisResult):
        """Send a gentle first warning."""
        title = "Focus Reminder"
        message = result.suggestion or f"Looks like you're {result.activity_description}. Time to refocus?"
        self._send(title, message, sound=False)

    def _send_urgent(self, result: AnalysisResult, off_task_duration: float):
        """Send an urgent escalated notification."""
        minutes = int(off_task_duration / 60)
        title = "⚠ Focus Alert"
        message = (
            result.suggestion
            or f"You've been off-task for {minutes}+ minutes ({result.activity_description}). Get back to work!"
        )
        self._send(title, message, sound=True)

    def _send(self, title: str, message: str, sound: bool = False):
        """Dispatch notification based on config style."""
        if self.config.notification_style == "banner":
            self._send_banner(title, message, sound)
        else:
            self._send_system(title, message, sound)

    def _send_system(self, title: str, message: str, sound: bool = False):
        """Send a macOS notification via osascript."""
        # Escape quotes for AppleScript
        title_escaped = title.replace('"', '\\"')
        message_escaped = message.replace('"', '\\"')

        sound_clause = ' sound name "Funk"' if sound else ""
        script = (
            f'display notification "{message_escaped}" '
            f'with title "{title_escaped}"{sound_clause}'
        )

        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                timeout=5,
            )
            if self.config.verbose:
                print(f"  [notifier] sent (system): {title} - {message}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if self.config.verbose:
                print(f"  [notifier] error: {e}")

    def _send_banner(self, title: str, message: str, sound: bool = False):
        """Send a full-width banner overlay via pre-compiled Swift binary."""
        # Compile on first use
        if self._banner_bin is None:
            self._banner_bin = _ensure_banner_compiled()
            if self._banner_bin is None:
                print("  [notifier] banner compile failed, falling back to system")
                self._send_system(title, message, sound)
                return

        # Clean up any finished banner processes
        self._banner_procs = [p for p in self._banner_procs if p.poll() is None]

        cmd = [str(self._banner_bin), title, message]
        if sound:
            cmd.append("--sound")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._banner_procs.append(proc)
            if self.config.verbose:
                print(f"  [notifier] sent (banner): {title} - {message}")
        except OSError as e:
            if self.config.verbose:
                print(f"  [notifier] banner error: {e}")
            self._send_system(title, message, sound)
