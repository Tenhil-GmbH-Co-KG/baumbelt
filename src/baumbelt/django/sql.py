import contextlib
import sys
from logging.config import dictConfig

from django.conf import settings
from django.db import connections


def _setup_initial_logging():
    if not settings.LOGGING:
        settings.LOGGING = {}

    if "loggers" not in settings.LOGGING:
        settings.LOGGING["loggers"] = {}

    if "version" not in settings.LOGGING:
        settings.LOGGING["version"] = 1

    if "handlers" not in settings.LOGGING:
        settings.LOGGING["handlers"] = {}

    if "console" not in settings.LOGGING["handlers"]:
        settings.LOGGING["handlers"]["console"] = {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
        }


@contextlib.contextmanager
def django_sql_debug(disable: bool = False):
    if disable:
        yield
        return

    _setup_initial_logging()

    prev_disable_existing = settings.LOGGING.get("disable_existing_loggers")
    settings.LOGGING["disable_existing_loggers"] = True

    prev_db_backends = settings.LOGGING["loggers"].get("django.db.backends")
    settings.LOGGING["loggers"]["django.db.backends"] = {
        "handlers": ["console"],
        "level": "DEBUG",
        "propagate": False,
    }
    dictConfig(settings.LOGGING)

    yield

    if prev_disable_existing is not None:
        settings.LOGGING["disable_existing_loggers"] = prev_disable_existing

    if prev_db_backends:
        settings.LOGGING["loggers"]["django.db.backends"] = prev_db_backends
    else:
        del settings.LOGGING["loggers"]["django.db.backends"]


total_query_count = 0


class count_queries:
    call_stacks = {}

    def __init__(self, name="", db_name="default"):
        self.name = name
        self.db_name = db_name

    def _get_padding(self):
        return " " * (count_queries.call_stacks[self]) * 3

    def __enter__(self):
        count_queries.call_stacks[self] = len(count_queries.call_stacks.keys())

        con = connections[self.db_name]
        self.queries_start = len(con.queries)

        return con

    def __exit__(self, exc_type, exc_val, exc_tb):
        con = connections[self.db_name]
        amount_queries = len(con.queries) - self.queries_start
        global total_query_count
        total_query_count += amount_queries

        blue = "\33[34m"
        reset = "\33[0m"
        name = f"'{self.name}' " if self.name else ""
        print(f"{self._get_padding()}{blue}{name}took {amount_queries} / {total_query_count} queries{reset}")

        del count_queries.call_stacks[self]
