import logging
from datetime import datetime, timedelta
from time import sleep

import requests
from requests.adapters import HTTPAdapter, DEFAULT_POOLSIZE, DEFAULT_POOLBLOCK

logger = logging.getLogger(__name__)


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

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None) -> requests.Response:
        start = datetime.now()
        end = start + timedelta(seconds=self.overall_timeout)
        attempts = 0
        last_error = None

        while True:
            time_til_end = end - datetime.now()
            max_timeout = max(time_til_end.total_seconds(), 0.0)
            if max_timeout < self.give_up_threshold:
                logger.debug(
                    f"no time left for another retry, aborting ({max_timeout=:.1f}, {self.give_up_threshold=:.1f})"
                )
                break

            planned_connect_timeout = max_timeout * self.connect_timeout_ratio
            max_connect_timeout = max(planned_connect_timeout, self.min_connect_timeout)
            max_read_timeout = max_timeout - max_connect_timeout

            connect_timeout = min(self.single_connect_timeout, max_connect_timeout)
            read_timeout = min(self.single_read_timeout, max_read_timeout)

            timeout = (connect_timeout, read_timeout)

            try:
                attempts += 1
                response = super().send(request, stream, timeout, verify, cert, proxies)

            except requests.ConnectTimeout as err:
                logger.debug(f"got a connect timeout, possibly retrying ({connect_timeout=:.1f}, {err=})")
                last_error = err

            except requests.ReadTimeout as err:
                logger.debug(f"got a read timeout, possibly retrying ({read_timeout=:.1f}, {err=})")
                last_error = err

            else:
                if (status := response.status_code) >= 500:
                    logger.debug(f"got a server error, possibly retrying ({status=})")
                else:
                    logger.debug(f"request finished ({status=}, {attempts=})")
                    response.raise_for_status()
                    return response

            backoff_index = min(attempts - 1, len(self.backoff_times) - 1)
            backoff = self.backoff_times[backoff_index]

            time_til_end = end - datetime.now()
            max_sleep = max(time_til_end.total_seconds(), 0.0)
            if max_sleep < backoff:
                logger.debug(f"no time left to wait for backoff, aborting ({max_sleep=:.1f}, {backoff=:.1f})")
                break

            sleep(backoff)

        logger.debug(f"request failed, raising error ({attempts=})")
        if last_error:
            raise last_error
        else:
            raise requests.Timeout(request=request)
