"""Screenshot capture using macOS builtins."""

import subprocess
from pathlib import Path

from focus.config import Config


def _get_display_count() -> int:
    """Return number of active displays via Quartz."""
    try:
        import Quartz
        (err, ids, count) = Quartz.CGGetActiveDisplayList(10, None, None)
        return count if err == 0 else 1
    except Exception:
        return 1


class ScreenCapture:
    def __init__(self, config: Config):
        self.config = config
        self.screenshot_dir = config.screenshot_path
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        self._display_count = _get_display_count()

    def capture(self) -> list[Path]:
        """Take a screenshot of each display, resize, and return the paths."""
        self._counter = (self._counter + 1) % self.config.max_screenshots
        paths: list[Path] = []

        for display in range(1, self._display_count + 1):
            filepath = self.screenshot_dir / f"focus_{self._counter}_d{display}.jpg"
            try:
                subprocess.run(
                    [
                        "screencapture", "-x",
                        "-D", str(display),
                        "-t", "jpg",
                        str(filepath),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )

                subprocess.run(
                    [
                        "sips",
                        "--resampleHeightWidthMax",
                        str(self.config.resize_max_dimension),
                        str(filepath),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )

                if self.config.verbose:
                    size_kb = filepath.stat().st_size / 1024
                    print(f"  [capture] {filepath.name} ({size_kb:.0f} KB)")

                paths.append(filepath)

            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                if self.config.verbose:
                    print(f"  [capture] display {display} error: {e}")

        return paths

    def cleanup(self):
        """Remove all screenshot files."""
        if self.screenshot_dir.exists():
            for f in self.screenshot_dir.glob("focus_*.jpg"):
                f.unlink(missing_ok=True)
