from unittest import TestCase

from baumbelt.retry import retry


class RetryTestCase(TestCase):
    def test_succeeds_immediately(self):
        @retry(max_tries=3)
        def succeed():
            return "ok"

        self.assertEqual(succeed(), "ok")

    def test_succeeds_after_retries(self):
        calls = 0

        @retry(exceptions=ValueError, max_tries=3)
        def fail_twice():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise ValueError("not yet")
            return "ok"

        self.assertEqual(fail_twice(), "ok")
        self.assertEqual(calls, 3)

    def test_raises_after_max_tries(self):
        calls = 0

        @retry(exceptions=ValueError, max_tries=3)
        def always_fail():
            nonlocal calls
            calls += 1
            raise ValueError("fail")

        with self.assertRaises(ValueError):
            always_fail()
        self.assertEqual(calls, 3)
