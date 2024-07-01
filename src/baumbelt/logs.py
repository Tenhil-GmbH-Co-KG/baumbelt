from typing import Callable, Any

from baumbelt.timing import MeasureTime


class HuggingLog:
    timer: MeasureTime
    name: str
    prefix: str
    logging_fn: Callable[[str], Any]

    def __init__(self, name: str, logging_fn: Callable[[str], Any] = print, prefix: str | None = None):
        self.name = name
        self.prefix = f"{prefix}: " if prefix else ""
        self.logging_fn = logging_fn

    def __enter__(self):
        self.logging_fn(f"{self.prefix}Start  '{self.name}'...")
        self.timer = MeasureTime().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.timer:
            return

        self.timer.__exit__(exc_type, exc_val, exc_tb)
        duration_str = f"{self.timer.duration} ({self.timer.duration.total_seconds():f}s total)"
        self.logging_fn(f"{self.prefix}Finish '{self.name}' in {duration_str}")
