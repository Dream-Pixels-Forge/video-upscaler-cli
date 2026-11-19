"""Progress parsing for ffmpeg stderr output."""

import re
from typing import Callable, Optional

_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")


class ProgressReporter:
    """Parses ffmpeg stderr lines and reports completion percent via callback."""

    def __init__(
        self,
        total_duration: float,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> None:
        self.total_duration = max(total_duration, 0.0)
        self.progress_callback = progress_callback

    def report(self, line: str) -> None:
        """Parse one stderr line; invoke callback when a time= stamp is present."""
        if self.progress_callback is None or self.total_duration <= 0:
            return
        match = _TIME_RE.search(line)
        if match is None:
            return
        hours, minutes, seconds = match.groups()
        elapsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        percent = min(100.0, max(0.0, elapsed / self.total_duration * 100.0))
        self.progress_callback(percent, line)
