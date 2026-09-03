import contextlib
import io
from unittest import TestCase

from baumbelt.logs import loop_log
from tests.utils import strip_after_seconds


class LoopLogTestCase(TestCase):
    def test_sized_iterable_yields_all_elements_unchanged(self):
        items = [1, 2, 3, 4, 5, 6]
        self.assertEqual(list(loop_log(items, times=3, use_print=True)), items)

    def test_sized_iterable_logs_fixed_number_of_times(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            list(loop_log([1, 2, 3, 4, 5, 6], item_name="job", times=3, use_print=True))

        lines = [strip_after_seconds(line) for line in buffer.getvalue().splitlines()]
        self.assertEqual(
            lines,
            [
                "processing job 1/6 after <t>s",
                "processing job 3/6 after <t>s",
                "processing job 5/6 after <t>s",
                "processed all 6 job items in <t>s",
            ],
        )

    def test_unsized_iterable_logs_every_element_when_seconds_is_none(self):
        buffer = io.StringIO()

        def generator():
            yield from ["a", "b", "c"]

        with contextlib.redirect_stdout(buffer):
            result = list(loop_log(generator(), seconds=None, use_print=True))

        self.assertEqual(result, ["a", "b", "c"])
        lines = [strip_after_seconds(line) for line in buffer.getvalue().splitlines()]
        self.assertEqual(
            lines,
            [
                "processing item #1 after <t>s",
                "processing item #2 after <t>s",
                "processing item #3 after <t>s",
                "processed all 3 items in <t>s",
            ],
        )

    def test_empty_iterable_logs_nothing_processed(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(list(loop_log([], use_print=True)), [])

        self.assertEqual(buffer.getvalue().strip(), "processed no items")
