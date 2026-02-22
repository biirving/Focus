"""Daily productivity summaries with relative ranking.

Rankings (low to high):
    waste of ATP < lazy < nothing special < productive < paul dirac

First day sets the baseline as "productive". Subsequent days are ranked
relative to the historical average productivity score.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from focus.config import Config

RANKINGS = ["waste of ATP", "lazy", "nothing special", "productive", "paul dirac"]

# Score thresholds relative to the historical average (ratio).
# e.g. if avg score = 60, then:
#   < 0.4 * avg  => waste of ATP
#   < 0.7 * avg  => lazy
#   < 1.1 * avg  => nothing special
#   < 1.4 * avg  => productive
#   >= 1.4 * avg => paul dirac
_RANK_THRESHOLDS = [0.4, 0.7, 1.1, 1.4]


class DailySummary:
    def __init__(self, config: Config):
        self._config = config
        self._base_dir = Path(config.log_dir).expanduser()
        self._summary_dir = self._base_dir / "summaries"
        self._summary_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = config.log_path
        self._usage_dir = self._base_dir / "usage"

    def generate_today(self) -> dict:
        """Generate and save today's summary from activity log + usage data."""
        today = date.today()
        summary = self._build_summary(today)
        summary["ranking"] = self._rank(summary["score"])
        self._save(today, summary)
        return summary

    def get_recent(self, days: int = 7) -> list[dict]:
        """Load summaries for the last N days (most recent first)."""
        results = []
        today = date.today()
        for i in range(days):
            day = today - timedelta(days=i)
            s = self._load(day)
            if s:
                results.append(s)
        return results

    # ── Score computation ──────────────────────────────────────────────────

    def _build_summary(self, day: date) -> dict:
        """Build a summary dict for the given day."""
        records = self._load_activity_log(day)
        usage = self._load_usage(day)

        total = len(records)
        on_task = sum(1 for r in records if r.get("status") == "on_task")
        off_task = sum(1 for r in records if r.get("status") == "off_task")
        on_break = sum(1 for r in records if r.get("status") == "break")

        on_task_pct = (on_task / total * 100) if total > 0 else 0
        off_task_pct = (off_task / total * 100) if total > 0 else 0

        # Score: 0-100 based on on-task ratio, with break time neutral
        productive_checks = on_task + off_task  # exclude breaks from ratio
        score = (on_task / productive_checks * 100) if productive_checks > 0 else 50

        # Top apps by usage
        top_apps = []
        if usage:
            sorted_apps = sorted(usage.items(), key=lambda x: x[1], reverse=True)
            for app, secs in sorted_apps[:5]:
                top_apps.append({"app": app, "minutes": round(secs / 60, 1)})

        # Total tracked time
        tracked_minutes = 0
        if records:
            first_ts = records[0].get("timestamp", "")
            last_ts = records[-1].get("timestamp", "")
            try:
                t0 = datetime.fromisoformat(first_ts)
                t1 = datetime.fromisoformat(last_ts)
                tracked_minutes = round((t1 - t0).total_seconds() / 60)
            except (ValueError, TypeError):
                pass

        return {
            "date": day.isoformat(),
            "display_date": day.strftime("%A, %b %-d"),
            "score": round(score, 1),
            "on_task_pct": round(on_task_pct, 1),
            "off_task_pct": round(off_task_pct, 1),
            "checks": total,
            "tracked_minutes": tracked_minutes,
            "top_apps": top_apps,
            "ranking": "",  # filled by caller
        }

    def _rank(self, score: float) -> str:
        """Rank today's score relative to historical average."""
        past = self.get_recent(days=30)
        # Exclude today if already saved
        today_str = date.today().isoformat()
        past_scores = [s["score"] for s in past if s["date"] != today_str and s.get("score", 0) > 0]

        if not past_scores:
            # First day — baseline is "productive"
            return "productive"

        avg = sum(past_scores) / len(past_scores)
        if avg == 0:
            return "productive"

        ratio = score / avg
        for i, threshold in enumerate(_RANK_THRESHOLDS):
            if ratio < threshold:
                return RANKINGS[i]
        return RANKINGS[-1]  # paul dirac

    # ── Storage ────────────────────────────────────────────────────────────

    def _save(self, day: date, summary: dict):
        path = self._summary_dir / f"{day.isoformat()}.json"
        path.write_text(json.dumps(summary, indent=2))

    def _load(self, day: date) -> dict | None:
        path = self._summary_dir / f"{day.isoformat()}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    # ── Data loaders ───────────────────────────────────────────────────────

    def _load_activity_log(self, day: date) -> list[dict]:
        """Load activity records for a specific day from the JSONL log."""
        if not self._log_path.exists():
            return []

        day_str = day.isoformat()
        records = []
        try:
            with open(self._log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        ts = record.get("timestamp", "")
                        if ts.startswith(day_str):
                            records.append(record)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return records

    def _load_usage(self, day: date) -> dict:
        """Load app usage data for a specific day."""
        path = self._usage_dir / f"{day.isoformat()}.json"
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            return data.get("apps", {})
        except (json.JSONDecodeError, OSError):
            return {}
