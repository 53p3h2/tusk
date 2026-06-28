from __future__ import annotations

import time
from enum import Enum


class ProcessStatus(Enum):
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    TERMINATED = "Terminated"


STATUS_COLORS: dict[ProcessStatus, str] = {
    ProcessStatus.RUNNING: "green",
    ProcessStatus.COMPLETED: "yellow",
    ProcessStatus.FAILED: "red",
    ProcessStatus.TERMINATED: "gray",
}


def format_duration(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes > 0:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def elapsed_since(start: float) -> float:
    return time.monotonic() - start
