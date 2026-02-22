"""Activity history tracking, streaks, and time budget enforcement."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from focus.config import Config
from focus.models import ActivityRecord, AnalysisResult, FocusStatus, TimeBudget


class ActivityTracker:
    def __init__(self, config: Config):
        self.config = config
        self.history: list[ActivityRecord] = []
        self._log_path = config.log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, result: AnalysisResult):
        """Add an analysis result to history and persist to log."""
        record = ActivityRecord.from_analysis(result)
        self.history.append(record)
        self._prune_history()
        self._append_log(record)

    def _prune_history(self):
        """Remove entries older than the history window."""
        cutoff = datetime.now() - timedelta(seconds=self.config.history_window)
        self.history = [r for r in self.history if r.timestamp >= cutoff]

        if len(self.history) > self.config.max_history_entries:
            self.history = self.history[-self.config.max_history_entries :]

    def _append_log(self, record: ActivityRecord):
        """Append a record to the persistent JSONL log."""
        try:
            with open(self._log_path, "a") as f:
                f.write(record.to_json_line() + "\n")
        except OSError as e:
            if self.config.verbose:
                print(f"  [activity] log write error: {e}")

    def get_current_streak(self) -> tuple[FocusStatus, float]:
        """Get the current activity streak (status, duration in seconds)."""
        if not self.history:
            return FocusStatus.UNKNOWN, 0.0

        current_status = self.history[-1].status
        streak_start = self.history[-1].timestamp

        for record in reversed(self.history[:-1]):
            if record.status != current_status:
                break
            streak_start = record.timestamp

        duration = (datetime.now() - streak_start).total_seconds()
        return current_status, duration

    def get_off_task_duration(self) -> float:
        """Get how long the user has been continuously off-task (seconds)."""
        status, duration = self.get_current_streak()
        if status == FocusStatus.OFF_TASK:
            return duration
        return 0.0

    def check_budgets(self, budgets: list[TimeBudget]) -> list[str]:
        """Check time budgets and return list of exceeded budget descriptions."""
        exceeded = []
        now = datetime.now()

        for budget in budgets:
            window = timedelta(minutes=budget.per_minutes)
            cutoff = now - window
            pattern_lower = budget.activity_pattern.lower()

            total_seconds = 0.0
            for i, record in enumerate(self.history):
                if record.timestamp < cutoff:
                    continue
                if pattern_lower in record.activity_description.lower():
                    # Estimate duration as time until next record or analysis interval
                    if i + 1 < len(self.history):
                        dt = (self.history[i + 1].timestamp - record.timestamp).total_seconds()
                    else:
                        dt = self.config.analysis_interval
                    total_seconds += dt

            total_minutes = total_seconds / 60
            if total_minutes > budget.max_minutes:
                exceeded.append(
                    f"{budget.activity_pattern}: {total_minutes:.0f}/{budget.max_minutes} min used"
                )

        return exceeded

    def format_history(self, last_n: int = 10) -> str:
        """Format recent history as text for Claude's context."""
        if not self.history:
            return "No activity recorded yet."

        entries = self.history[-last_n:]
        lines = []
        for record in entries:
            ts = record.timestamp.strftime("%H:%M:%S")
            lines.append(
                f"- [{ts}] {record.status.value}: {record.activity_description}"
            )

        status, duration = self.get_current_streak()
        lines.append(f"\nCurrent streak: {status.value} for {duration:.0f}s")

        return "\n".join(lines)
