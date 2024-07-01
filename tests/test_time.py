import re
import time
from datetime import datetime
from unittest import TestCase

from baumbelt.timing import MeasureTime


class MeasureTimeTestCase(TestCase):

    def test_duration(self):
        t0 = datetime.now()

        with MeasureTime() as mt:
            time.sleep(0.3)
            tduration = datetime.now() - t0

        self.assertAlmostEqual(mt.duration.total_seconds(), tduration.total_seconds(), places=2)

    def test_duration_string(self):
        with MeasureTime() as mt:
            time.sleep(0.3)

        formatted_duration = str(mt)
        match = re.search(r"^0:00:00\.3\d+ \(0\.3\d+s\)$", formatted_duration)
        self.assertIsNotNone(match)
