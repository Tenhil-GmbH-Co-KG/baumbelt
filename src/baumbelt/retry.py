import random
import time
from functools import wraps
from typing import Any, Callable, Type


def retry(
    exceptions: Type[Exception] | tuple[Type[Exception]] = Exception,
    max_tries: int = -1,
    retry_delay: int = 0,
    backoff: float = 1.0,
    jitter: int = 0,
    logging_fn: Callable[[str], Any] = None,
):
    """Retries the wrapped function should any of the passed exceptions occur.

    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param max_tries: the maximum number of attempts. default: -1 (infinite).
    :param retry_delay: initial delay between attempts. default: 0.
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logging_fn: if passed, called with a warning message on each failed attempt.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tries = max_tries
            delay = retry_delay
            while tries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    tries -= 1
                    if not tries:
                        raise

                    if logging_fn:
                        logging_fn(f"{e}, retrying {func.__name__} in {delay} seconds...")

                    time.sleep(delay)
                    delay *= backoff

                    if isinstance(jitter, tuple):
                        delay += random.uniform(*jitter)
                    else:
                        delay += jitter

        return wrapper

    return decorator
