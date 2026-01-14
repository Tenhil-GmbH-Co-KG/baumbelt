import logging
from datetime import datetime, timedelta
from time import sleep

from requests import Timeout, Response
from requests.adapters import HTTPAdapter, DEFAULT_POOLSIZE, DEFAULT_POOLBLOCK

logger = logging.getLogger(__name__)


class OverallTimeout(Timeout):
    pass


class SmartRetryHTTPAdapter(HTTPAdapter):
    """
    Adapter that combines multiple request timeout strategies:
    - all times specified in seconds as float
    - overall_timeout specifies the total time after which an end of the request is guaranteed
    - single_connect_timeout and single_read_timeout specify a timeout for individual requests
    - if individual requests time out or fail with server errors (5XX), they are retried as long as there still time
      left before the overall timeout
    - the number of retries does not matter - if the request fails fast, more retries may fit into the overall timeout
      window
    - a tuple of backoff_times is used between failing requests - if there are more retries than elements, it will
      re-use the last element
    - give_up_threshold specifies the time at which, if the remaining time until the overall timeout falls below it,
      no more retries are attempted (because such a low timeout for a single request would make no sense)
    """

    def __init__(
        self,
        overall_timeout: float = 50.0,
        single_connect_timeout: float = 5.0,
        single_read_timeout: float = 45.0,
        backoff_times: tuple[float] = (0.1, 0.25, 0.5, 1.0, 2.0),
        give_up_threshold: float = 1.0,
        pool_connections=DEFAULT_POOLSIZE,
        pool_maxsize=DEFAULT_POOLSIZE,
        pool_block=DEFAULT_POOLBLOCK,
    ):
        super().__init__(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            pool_block=pool_block,
        )

        self.overall_timeout: float = overall_timeout
        self.single_connect_timeout: float = single_connect_timeout
        self.single_read_timeout: float = single_read_timeout
        self.backoff_times: tuple[float] = backoff_times
        self.give_up_threshold: float = give_up_threshold

        self.single_timeout: float = self.single_connect_timeout + self.single_read_timeout
        self.connect_timeout_ratio: float = self.single_connect_timeout / self.single_timeout
        self.min_connect_timeout: float = self.give_up_threshold / 2

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None) -> Response:
        start = datetime.now()
        end = start + timedelta(seconds=self.overall_timeout)
        attempts = 0
        response: Response | None = None
        last_error: Timeout | None = None
        last_duration: float | None = None

        while True:
            time_til_end = end - datetime.now()
            max_timeout = max(time_til_end.total_seconds(), 0.0)
            if max_timeout < self.give_up_threshold:
                break

            planned_connect_timeout = max_timeout * self.connect_timeout_ratio
            max_connect_timeout = max(planned_connect_timeout, self.min_connect_timeout)
            max_read_timeout = max_timeout - max_connect_timeout

            connect_timeout = min(self.single_connect_timeout, max_connect_timeout)
            read_timeout = min(self.single_read_timeout, max_read_timeout)

            timeout = (connect_timeout, read_timeout)

            attempts += 1
            req_start = datetime.now()
            try:
                response = super().send(request, stream, timeout, verify, cert, proxies)
                if response.status_code < 500:
                    break

            except Timeout as err:
                last_error = err

            finally:
                last_duration = (datetime.now() - req_start).total_seconds()

            backoff_index = min(attempts - 1, len(self.backoff_times) - 1)
            backoff = self.backoff_times[backoff_index]

            time_til_end = end - datetime.now()
            max_sleep = max(time_til_end.total_seconds(), 0.0)
            if max_sleep < backoff:
                break

            sleep(backoff)

        status_str = f"status={response.status_code}" if response else "status=none"
        attempts_str = f"attempts={attempts}"
        duration_str = f"last_duration={last_duration:.3f}" if last_duration else "last_duration=none"
        error_str = f"last_error={type(last_error).__name__}" if last_error else "last_error=none"

        logger.debug(f"{status_str}, {attempts_str}, {duration_str}, {error_str}")

        if response:
            response.raise_for_status()
            return response

        raise last_error or OverallTimeout(request=request)
