import inspect
import time
from datetime import timedelta, datetime
from typing import Literal

try:
    from django.db import connections
    from django.db.backends.dummy.base import DatabaseWrapper

    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False


UNSET = object()


class MeasureTime:
    duration: timedelta
    start: datetime

    def __enter__(self):
        self.start = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = datetime.now() - self.start

    def __str__(self):
        if self.duration is None:
            self.duration = datetime.now() - self.start
        return f"{self.duration} ({self.duration.total_seconds()}s)"


class Timer:
    call_stacks = {}
    last_tap = None
    last_tap_queries = 0

    creset = "\33[0m"
    cgreen = "\33[32m"
    cgrey = "\33[90m"

    def __init__(
        self,
        name: str = None,
        resolution: Literal["s"] | Literal["ms"] = "s",
        disable: bool = False,
        db_name: str = "default",
        disable_queries: bool = UNSET,
    ):
        if name is None:
            _, _, _, function_name, _, _ = inspect.stack()[1]
            name = function_name

        self.name = name
        self.resolution = resolution
        self.disable = disable
        self.db_name = db_name

        # If not specified, use them if django is available
        if disable_queries is UNSET:
            disable_queries = not DJANGO_AVAILABLE

        # Fail if mentioned explicitely, but Django is not present.
        elif disable_queries is False and not DJANGO_AVAILABLE:
            raise ValueError(
                "Queries can't be tracked if Django is not installed. Hint: remove your `disable_queries` argument."
            )

        self.enable_queries = not disable_queries

    def _get_padding(self):
        return " " * (Timer.call_stacks[self]) * 2

    def _convert_to_resolution(self, delta) -> tuple[int, str]:
        if self.resolution == "ms":
            return delta * 1000, self.resolution

        return delta, self.resolution

    def __enter__(self):
        Timer.call_stacks[self] = len(Timer.call_stacks.keys())

        if self.disable:
            return self

        if self.enable_queries:
            con: DatabaseWrapper = connections[self.db_name]
            self.queries_start = len(con.queries)
            self.last_tap_queries = self.queries_start

        msg = f"{self._get_padding()}v '{self.name}' started..."
        print(f"{self.cgreen}{msg}{self.creset}")
        self.start = time.time()
        self.last_tap = self.start

        return self

    def tap(self, name: str):
        now = time.time()
        last_tap = self.last_tap
        self.last_tap = now
        if self.disable:
            return

        padded_tap_name = f"'{name}'".ljust(30)
        msg = f"{self._get_padding()} > {padded_tap_name}"
        msgs = []

        delta = now - last_tap
        delta, unit = self._convert_to_resolution(delta)
        duration, _ = self._convert_to_resolution(now - self.start)

        msgs.append(f"took {delta:.4f}{unit} (at {duration:.4f}{unit})")

        if self.enable_queries:
            con: DatabaseWrapper = connections[self.db_name]
            queries_done = len(con.queries)
            amount_queries = queries_done - self.last_tap_queries
            self.last_tap_queries = queries_done
            msgs.append(f"had {amount_queries} queries")

        msg = msg + ", ".join(msgs)
        print(f"{self.cgrey}{msg}{self.creset}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.disable:
            del Timer.call_stacks[self]
            return

        msg = f"{self._get_padding()}ʌ '{self.name}'"
        end = time.time()
        duration = end - self.start
        self.total = duration
        duration, unit = self._convert_to_resolution(duration)
        msg += f" took {duration:.4f}{unit},"

        if self.enable_queries:
            con: DatabaseWrapper = connections[self.db_name]
            queries_done = len(con.queries) - self.queries_start
            msg += f" had {queries_done} queries,"

        print(f"{self.cgreen}{msg[:-1]}{self.creset}")

        del Timer.call_stacks[self]
