from django.db import connections

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
