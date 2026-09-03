import logging
from datetime import datetime
from math import ceil
from typing import Callable, Any, Iterable, Sized

from baumbelt.timing import MeasureTime

logger = logging.getLogger(__name__)


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


def _seconds_since(dt: datetime):
    return (datetime.now() - dt).total_seconds()


def loop_log(iterable: Iterable | Sized, item_name="item", times=5, seconds=30, use_print=False):
    """
    Automatically takes care of logging (the right amount) when iterating over lists or iterators.

    :param iterable: any iterable object. If a length can be determined (like for lists or querysets), it logs
    a fixed number of times during the loop. Otherwise (for iterators) it logs based on the passed time to
    basically show the throughput.

    :param item_name: can be used to replace the word "item" to fit the log output to the situation, e.g.
    "job" when iterating over a list of jobs.

    :param times: (only for length-based logging) example: 10 means that it will log 10 times in total, meaning
    before each of 10 equally sized batches.

    :param seconds: (only for time-based logging) example: 10 means that it will log (at least) every 10 seconds
    showing the throughout.
    """
    if use_print:
        log = print
    else:
        log = logger.debug
    idx = -1
    start_time = datetime.now()
    if hasattr(iterable, "__len__"):
        assert times is None or (isinstance(times, int) and times >= 0)
        amount = len(iterable)
        log_amount = ceil(amount / times) if amount and times else 1
        for idx, elem in enumerate(iterable):
            if idx % log_amount == 0:
                log(f"processing {item_name} {idx + 1}/{amount} after {_seconds_since(start_time):.1f}s")
            yield elem
    else:
        last_log_time = start_time
        for idx, elem in enumerate(iterable):
            if seconds is None or _seconds_since(last_log_time) >= seconds:
                log(f"processing {item_name} #{idx + 1} after {_seconds_since(start_time):.1f}s")
                last_log_time = datetime.now()
            yield elem
    item_name_plural = "items" if item_name == "item" else f"{item_name} items"
    if amount := idx + 1:
        log(f"processed all {amount} {item_name_plural} in {_seconds_since(start_time):.1f}s")
    else:
        log(f"processed no {item_name_plural}")
