"""Data models for Focus OS."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class FocusStatus(str, Enum):
    ON_TASK = "on_task"
    OFF_TASK = "off_task"
    BREAK = "break"
    UNKNOWN = "unknown"


@dataclass
class AnalysisResult:
    status: FocusStatus
    activity_description: str
    confidence: float
    reasoning: str
    suggestion: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        status_str = data.get("status", "unknown")
        try:
            status = FocusStatus(status_str)
        except ValueError:
            status = FocusStatus.UNKNOWN
        return cls(
            status=status,
            activity_description=data.get("activity_description", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=data.get("reasoning", ""),
            suggestion=data.get("suggestion"),
        )


@dataclass
class ActivityRecord:
    timestamp: datetime
    activity_description: str
    status: FocusStatus
    confidence: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "activity_description": self.activity_description,
            "status": self.status.value,
            "confidence": self.confidence,
        }

    def to_json_line(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_analysis(cls, result: AnalysisResult) -> "ActivityRecord":
        return cls(
            timestamp=result.timestamp,
            activity_description=result.activity_description,
            status=result.status,
            confidence=result.confidence,
        )


@dataclass
class TimeBudget:
    activity_pattern: str
    max_minutes: int
    per_minutes: int = 60  # default: per hour
