from unittest import TestCase

from baumbelt.requests import OverallTimeout


class OverallTimeoutStrTestCase(TestCase):
    def test_str_includes_attempts_and_url(self):
        err = OverallTimeout(attempts=3, url="api.example.com/v1/resource?foo=bar")
        self.assertEqual(str(err), "OverallTimeout(attempts=3,url=api.example.com/v1/resource?foo=bar)")
