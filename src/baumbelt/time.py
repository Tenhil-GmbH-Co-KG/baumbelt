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
