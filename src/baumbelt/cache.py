import pickle
from functools import wraps, partial
from pathlib import Path
from typing import Callable

Empty = object()


def _unpickle(destination: Path):
    try:
        with open(destination, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return Empty


def pklcache(func: Callable | None = None, **options):
    """
    A decorator to quickly cache a functions return value. It is cached as
    pickled file, and unpickled again on the next invocation.
    """

    if func is None:
        return partial(pklcache, **options)

    force_refresh = options.get("force_refresh", False)
    destination = options.get("destination", None)
    if destination is None:
        destination = func.__name__

    @wraps(func)
    def wrapped(*args, **kwargs):
        dest_path = Path(f"{destination}.pkl")
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if not force_refresh and (result := _unpickle(dest_path)) is not Empty:
            return result

        result = func(*args, **kwargs)
        with open(dest_path, "wb") as f:
            pickle.dump(result, f)

        return result

    return wrapped
