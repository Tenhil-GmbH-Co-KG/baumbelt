import time
from datetime import timedelta, datetime


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

    creset = "\33[0m"
    cgreen = "\33[32m"
    cgrey = "\33[90m"

    def __init__(self, name: str, resolution="s", disable=0):
        self.name = name
        self.resolution = resolution
        self.disable = disable

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

        msg = f"{self._get_padding()}v'{self.name}' started..."
        print(f"{self.cgreen}{msg}{self.creset}")
        self.start = time.time()
        self.last_tap = self.start

        return self

    def tap(self, name: str):
        now = time.time()

        if not self.disable:
            delta = now - self.last_tap
            delta, unit = self._convert_to_resolution(delta)
            duration, _ = self._convert_to_resolution(now - self.start)

            padded_name = f"'{name}'".ljust(40)

            msg = f"{self._get_padding()}  > {padded_name} took {delta:.4f}{unit} (at {duration:.4f}{unit})"
            print(f"{self.cgrey}{msg}{self.creset}")

        self.last_tap = now

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.disable:
            del Timer.call_stacks[self]
            return

        end = time.time()
        duration = end - self.start
        duration, unit = self._convert_to_resolution(duration)

        msg = f"{self._get_padding()}ʌ'{self.name}' took {duration:.4f}{unit}"
        print(f"{self.cgreen}{msg}{self.creset}")

        del Timer.call_stacks[self]
