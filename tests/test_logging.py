import contextlib
import io
from unittest import TestCase

from baumbelt.logs import HuggingLog
from tests.utils import strip_duration_and_seconds


class HuggingLogTestCase(TestCase):

    def test_hugging_log_print_default(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), HuggingLog("cross-compile doom"):
            ...

        msg = strip_duration_and_seconds(buffer.getvalue())
        self.assertEqual(msg, "Start  'cross-compile doom'...\nFinish 'cross-compile doom' in <duration>\n")

    def test_hugging_log_logging_fn(self):
        buffer = ""

        def logging_fn(string):
            nonlocal buffer
            buffer += string

        with HuggingLog("cross-compile doom", logging_fn=logging_fn):
            ...

        msg = strip_duration_and_seconds(buffer)
        self.assertEqual(msg, "Start  'cross-compile doom'...Finish 'cross-compile doom' in <duration>")

    def test_hugging_log_prefix(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), HuggingLog("cross-compile doom", prefix="[ARM]"):
            ...

        msg = strip_duration_and_seconds(buffer.getvalue())
        self.assertEqual(
            msg,
            "[ARM]: Start  'cross-compile doom'...\n[ARM]: Finish 'cross-compile doom' in <duration>\n",
        )
