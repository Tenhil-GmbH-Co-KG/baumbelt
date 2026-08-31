from unittest import TestCase
from unittest.mock import patch

from requests import ConnectionError, HTTPError, Request, Response
from requests.adapters import HTTPAdapter

from baumbelt.requests import OverallTimeout, SmartRetryHTTPAdapter


class OverallTimeoutStrTestCase(TestCase):
    def test_str_includes_attempts_and_url(self):
        err = OverallTimeout(attempts=3, url="api.example.com/v1/resource?foo=bar")
        self.assertEqual(str(err), "OverallTimeout(attempts=3,url=api.example.com/v1/resource?foo=bar)")


class SmartRetryHTTPAdapterSendTestCase(TestCase):
    """
    Patches the underlying HTTPAdapter.send, so the adapter's retry loop can be driven with arbitrary
    responses and errors without doing actual HTTP.
    """

    def setUp(self):
        # A backoff longer than the overall timeout makes the loop stop after the first failed attempt, a
        # backoff of 0.0 lets it retry immediately - combining them controls the number of attempts per test.
        self.adapter = SmartRetryHTTPAdapter(
            overall_timeout=1.5,
            single_connect_timeout=0.5,
            single_read_timeout=1.0,
            backoff_times=(0.0, 0.0, 60.0),
        )
        self.request = Request(method="GET", url="https://foo.bar/some-resource/").prepare()

    def _send(self, *outcomes):
        with patch.object(HTTPAdapter, "send", side_effect=outcomes) as self.send_mock:
            return self.adapter.send(self.request)

    @staticmethod
    def _response(status_code: int) -> Response:
        response = Response()
        response.status_code = status_code
        response.url = "https://foo.bar/some-resource/"
        return response

    def test_connection_error_is_retried_until_it_succeeds(self):
        response = self._send(
            ConnectionError("Remote end closed connection without response"),
            ConnectionError(104, "Connection reset by peer"),
            self._response(200),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.send_mock.call_count, 3)

    def test_connection_error_is_raised_once_no_time_for_retries_is_left(self):
        with self.assertRaises(ConnectionError):
            self._send(
                ConnectionError("Connection aborted."),
                ConnectionError("Connection aborted."),
                ConnectionError("Connection aborted."),
            )

        self.assertEqual(self.send_mock.call_count, 3)

    def test_connection_error_is_not_masked_by_a_stale_server_error_response(self):
        with self.assertRaises(ConnectionError):
            self._send(
                self._response(503),
                self._response(503),
                ConnectionError("Connection aborted."),
            )

    def test_client_error_is_raised_without_being_retried(self):
        with self.assertRaises(HTTPError):
            self._send(self._response(404), self._response(200))

        self.assertEqual(self.send_mock.call_count, 1)
