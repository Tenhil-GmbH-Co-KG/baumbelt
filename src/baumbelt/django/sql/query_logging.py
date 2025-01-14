import contextlib
import time

import pygments
import sqlparse
from django.core.management.color import supports_color
from django.db import connection
from pygments.formatters.terminal import TerminalFormatter
from pygments.lexers import SqlLexer
from sqlparse.sql import Parenthesis, IdentifierList, Identifier

MAX_CHARS_TO_PARSE = 5_000
UNPARSED_CHARS_TO_PRINT = 400


class DjangoSQLWrapper:
    def __init__(self, indent=False, max_arguments=5, truncate_unparsable=True):
        self.do_indent = indent
        self.max_arguments = max_arguments
        self.truncate_unparsable = truncate_unparsable

    def __call__(self, execute, sql, params, many, context):
        start = time.monotonic()
        try:
            return execute(sql, params, many, context)
        except Exception as e:
            raise e
        finally:
            duration = time.monotonic() - start
            sql_log = self.log_executemany(sql, params) if many else self.log_execute(sql % params)
            print(f"({duration:.2f}s)\n{sql_log}")

    def truncate_arguments(self, sql):
        parsed = sqlparse.parse(sql)
        modified_statements = []

        for statement in parsed:
            stmt = self._trim_in(statement.tokens)
            modified_statements.append("".join([str(token) for token in stmt]))

        return " ".join(modified_statements)

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

    def log_executemany(self, sql, param_list):
        log = ""
        for param_tuple in param_list:
            log += f"{self.log_execute(sql % param_tuple)}\n"
        return log

    def log_execute(self, sql):
        sql_length = len(sql)
        if sql_length > MAX_CHARS_TO_PARSE:
            if self.truncate_unparsable:
                sql = f"{sql[:UNPARSED_CHARS_TO_PRINT]} <{sql_length - UNPARSED_CHARS_TO_PRINT} chars hidden>"

            return sql

        formatted = sqlparse.format(sql, reindent=self.do_indent)
        if self.max_arguments >= 0:
            truncated = self.truncate_arguments(sql=formatted)
        else:
            truncated = formatted

        if supports_color():
            pretty_sql = pygments.highlight(truncated, SqlLexer(), TerminalFormatter())
        else:
            pretty_sql = truncated

        return pretty_sql


@contextlib.contextmanager
def django_sql_debug(indent: bool = False, max_arguments: int = 5, truncate_unparsable: bool = True):
    dj_sql_wrap = DjangoSQLWrapper(indent=indent, max_arguments=max_arguments, truncate_unparsable=truncate_unparsable)
    with connection.execute_wrapper(dj_sql_wrap):
        yield
