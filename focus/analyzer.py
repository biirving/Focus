"""Claude API vision analysis for screenshots."""

import base64
import json
from pathlib import Path

import anthropic

from focus.config import Config
from focus.models import AnalysisResult, FocusStatus

SYSTEM_PROMPT_TEMPLATE = """You are Focus OS, an AI productivity monitor. You analyze screenshots of a user's screen to determine if they are staying on task.

## User's Focus Rules
{prompt_content}

## Recent Activity History
{activity_history}

## Your Task
Analyze the screenshot and determine if the user is on-task, off-task, or on a break.

Consider:
- What application/website is visible
- Whether it matches the allowed/blocked activities above
- The recent activity history (are they in a streak of off-task behavior?)
- Time budget limits if applicable
- Break policies

Respond with ONLY valid JSON (no markdown fences, no extra text):
{{
    "status": "on_task" | "off_task" | "break",
    "activity_description": "brief description of what the user is doing",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation of your assessment",
    "suggestion": "optional helpful suggestion if off-task, null if on-task"
}}"""


class Analyzer:
    def __init__(self, config: Config):
        self.config = config
        self.client = anthropic.Anthropic()

    def analyze(
        self,
        screenshot_path: Path | list[Path],
        prompt_content: str,
        activity_history: str,
    ) -> AnalysisResult | None:
        """Analyze one or more screenshots using Claude's vision API."""
        try:
            paths = screenshot_path if isinstance(screenshot_path, list) else [screenshot_path]
            paths = [p for p in paths if p.exists()]
            if not paths:
                return None

            content: list[dict] = []
            for p in paths:
                image_data = base64.standard_b64encode(p.read_bytes()).decode("utf-8")
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data,
                    },
                })

            label = "this screenshot" if len(paths) == 1 else "these screenshots (one per display)"
            content.append({
                "type": "text",
                "text": f"Analyze {label}. Respond with JSON only.",
            })

            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                prompt_content=prompt_content,
                activity_history=activity_history or "No recent activity recorded yet.",
            )

            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )

            return self._parse_response(response)

        except anthropic.APIError as e:
            if self.config.verbose:
                print(f"  [analyzer] API error: {e}")
            return None
        except Exception as e:
            if self.config.verbose:
                print(f"  [analyzer] error: {e}")
            return None

    def _parse_response(self, response) -> AnalysisResult | None:
        """Parse Claude's response into an AnalysisResult."""
        text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            data = json.loads(text)
            result = AnalysisResult.from_dict(data)

            if self.config.verbose:
                print(f"  [analyzer] {result.status.value}: {result.activity_description} ({result.confidence:.0%})")

            return result

        except (json.JSONDecodeError, KeyError) as e:
            if self.config.verbose:
                print(f"  [analyzer] parse error: {e}\n  response: {text[:200]}")
            return None
