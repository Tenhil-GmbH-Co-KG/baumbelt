from datetime import date
from unittest import TestCase

from baumbelt.grouping import group_by_key


class GroupByKeyTestCase(TestCase):

    def test_group_by_callable_key(self):
        iterable = [
            date(2020, 1, 1),
            date(2021, 2, 2),
            date(2022, 3, 3),
            date(2023, 4, 4),
        ]

        grouped = group_by_key(iterable, "weekday")
        self.assertEqual(
            grouped,
            {
                1: [date(2021, 2, 2), date(2023, 4, 4)],
                2: [date(2020, 1, 1)],
                3: [date(2022, 3, 3)],
            },
        )

    def test_group_by_key(self):
        iterable = [
            date(2020, 1, 1),
            date(2021, 2, 2),
            date(2022, 3, 3),
            date(2023, 4, 4),
        ]

        grouped = group_by_key(iterable, "day")
        self.assertEqual(
            grouped,
            {
                1: [date(2020, 1, 1)],
                2: [date(2021, 2, 2)],
                3: [date(2022, 3, 3)],
                4: [date(2023, 4, 4)],
            },
        )
