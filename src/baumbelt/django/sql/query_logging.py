import contextlib
import logging
import sys
from logging.config import dictConfig

import pygments
import sqlparse
from django.conf import settings
from django.core.management.color import supports_color
from pygments.formatters.terminal import TerminalFormatter
from pygments.lexers import SqlLexer
from sqlparse.sql import Parenthesis, IdentifierList, Identifier


class SqlFormatter(logging.Formatter):
    do_indent: bool
    max_arguments: int

    def __init__(self, *args, **kwargs):
        constants = kwargs.pop("constants", {})
        super().__init__(*args, **kwargs)

        self.do_indent = constants.get("indent", False)
        self.max_arguments = constants.get("max_arguments", 5)

    def format(self, record):
        sql = record.__dict__.get("sql")
        duration = record.__dict__.get("duration")

        if sql is None or duration is None:
            return super().format(record)

        formatted = sqlparse.format(sql, reindent=self.do_indent)
        if self.max_arguments >= 0:
            truncated = self.truncate_arguments(sql=formatted)
        else:
            truncated = formatted

        if supports_color():
            pretty_sql = pygments.highlight(truncated, SqlLexer(), TerminalFormatter())
        else:
            pretty_sql = truncated

        return f"({duration:.2f}s)\n{pretty_sql}"

    def _trim_in(self, tokens):
        """
        Looks for an IN expression, and truncates its arguments to max_items.

        ```
        WHERE "table"."id" IN (0,1,2, ..., 999)
        ```
        """

        for i, token in enumerate(tokens):
            if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "IN":
                # The next two tokens should be Whitespace followed by Parenthesis.
                next_token_parenthesis = tokens[i + 2]

                if isinstance(next_token_parenthesis, Parenthesis):
                    truncated_arguments = self._trim_in_arguments(next_token_parenthesis)
                    tokens[i + 2] = truncated_arguments

            if isinstance(token, (IdentifierList, Identifier)):
                self._trim_in(token.tokens)

            if token.is_group:
                self._trim_in(token.tokens)

        return tokens

    def _trim_in_arguments(self, parenthesis_token):
        arguments = parenthesis_token.value.strip("()").split(",")
        if len(arguments) <= self.max_arguments or len(arguments) < 3:
            return parenthesis_token

        last_arg = arguments[-1]
        next_n_args = arguments[: self.max_arguments - 1]

        # When indenting, this represents the amount of spaces to the left.
        indentation = len(last_arg) - len(last_arg.strip()) - 1

        args_removed = len(arguments) - len(next_n_args) - 1
        truncation = f"{indentation * ' '}/* {args_removed} truncated */"

        if self.do_indent:
            truncation = f"\n{truncation}"

        first_args_str = ",".join(next_n_args)
        new_value = f"({first_args_str},{truncation}{last_arg})"
        return Parenthesis(sqlparse.sql.TokenList(sqlparse.parse(new_value)[0].tokens))

    def truncate_arguments(self, sql):
        parsed = sqlparse.parse(sql)
        modified_statements = []

        for statement in parsed:
            stmt = self._trim_in(statement.tokens)
            modified_statements.append("".join([str(token) for token in stmt]))

        return " ".join(modified_statements)


def _setup_initial_logging(indent: bool, max_arguments: int):
    if not settings.LOGGING:
        settings.LOGGING = {}

    if "loggers" not in settings.LOGGING:
        settings.LOGGING["loggers"] = {}

    if "version" not in settings.LOGGING:
        settings.LOGGING["version"] = 1

    if "handlers" not in settings.LOGGING:
        settings.LOGGING["handlers"] = {}

    if "sqlhandler" not in settings.LOGGING["handlers"]:
        settings.LOGGING["handlers"]["sqlhandler"] = {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "sql",
            "stream": sys.stdout,
        }

    if "formatters" not in settings.LOGGING:
        settings.LOGGING["formatters"] = {}

    # Always re-define the formatter, in case different arguments are used (indent, max_arguments).
    settings.LOGGING["formatters"]["sql"] = {
        "()": "baumbelt.django.sql.SqlFormatter",
        "constants": {
            "indent": indent,
            "max_arguments": max_arguments,
        },
    }


@contextlib.contextmanager
def django_sql_debug(disable: bool = False, indent: bool = False, max_arguments: int = 5):
    if disable:
        yield
        return

    _setup_initial_logging(indent=indent, max_arguments=max_arguments)

    prev_disable_existing = settings.LOGGING.get("disable_existing_loggers")
    settings.LOGGING["disable_existing_loggers"] = True

    prev_db_backends = settings.LOGGING["loggers"].get("django.db.backends")
    settings.LOGGING["loggers"]["django.db.backends"] = {
        "handlers": ["sqlhandler"],
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
