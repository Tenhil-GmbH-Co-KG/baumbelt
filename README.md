# baumbelt

This is a collection of utilities we, at Tenhil, find useful when developing in Python or specifically Django.
`baumbelt` is an acronym for:

**B**asic **A**uxiliary **U**tility **M**ethods tool**belt**.

Also, *Baum* is the german word for *trees*, and we happen to just like them. A lot.

# Installation

`pip install baumbelt`

# Utilities

`baumbelt` contains both python- and django-specific utilities. If you don't have Django installed, you still can use the vanilla Python utilities.
Everything imported from `baumbelt.django` assumes Django to be installed.

## EnumContainsMeta

`baumbelt.enum.EnumContainsMeta` offers a metaclass, that adds the syntactic sugar of member checks. The default `Enum` only allows checks for values:

```python
from enum import Enum
from baumbelt.enums import EnumContainsMeta


class AtomEnum(Enum, metaclass=EnumContainsMeta):
    hydrogen = 1
    helium = 2


"hydrogen" in AtomEnum  # True
2 in AtomEnum  # True
"water" in AtomEnum  # False
```

## MeasureTime

The `baumbelt.time.MeasureTime` class can be used as a context manager to have a syntactically appealing way to measure the time a block of code takes.
The following two snippets produce the same result.

Vanilla:

```python
from datetime import datetime

t0 = datetime.now()
this_call_takes_a_while()
tend = datetime.now() - t0

print(f"{tend} ({tend.total_seconds()}s)")

```

`MeasureTime`:

```python
from baumbelt.timing import MeasureTime

with MeasureTime() as mt:
    this_call_takes_a_while()
    print(mt)
```

## Timer

`baumbelt.time.timer` is a more flexible utility compared to `MeasureTime`. It additionally allows to *tap* the current time.\
This snippet:

```python
import time
from baumbelt.timing import Timer


def fetch_raw_data():
    with Timer() as t:
        time.sleep(0.8)
        t.tap("got users")
        time.sleep(2)
        t.tap("got events")
        time.sleep(0.5)


def enrich_data():
    with Timer("enrich_data", resolution="ms") as t:
        time.sleep(0.1)
        t.tap("enriched-step-1")
        time.sleep(0.02)
        t.tap("enriched-step-2")


with Timer("main") as t:
    fetch_raw_data()

    t.tap("enriching..")
    enrich_data()

```

produces the following output:

```text
v 'main' started...
  v 'fetch_raw_data' started...
    > 'got users'                              took 0.8002s (at 0.8002s)
    > 'got events'                             took 2.0003s (at 2.8005s)
  ʌ 'fetch_raw_data' took 3.3008s
  > 'enriching..'                            took 3.3009s (at 3.3009s)
  v 'enrich_data' started...
    > 'enriched-step-1'                        took 100.1561ms (at 100.1561ms)
    > 'enriched-step-2'                        took 20.1433ms (at 120.2993ms)
  ʌ 'enrich_data' took 120.3260ms
ʌ 'main' took 3.4212s
```

If you don't pass a `name` to `Timer()`, it will use the `inspect` package to find the caller function's name.

### Query Support

When Django is available, the `Timer` will also track the queries fired per block. Given this example code:

```python
with Timer(resolution="s") as t:
    author, _ = Author.objects.get_or_create(name="Martin Heidegger")
    t.tap("author")
    book, _ = Book.objects.get_or_create(title="Sein und Zeit", author=author)
    t.tap("book")
```

it will yield this output:

```text
v 'handle' started...
 > 'author'                      took 0.0060s (at 0.0060s), had 4 queries
 > 'book'                        took 0.0063s (at 0.0122s), had 4 queries
ʌ'handle' took 0.0122s, had 8 queries
```

If you don't want this, pass `disable_queries=True` to `Timer()`.

## HuggingLog

`baumbelt.logging.HuggingLog` offers a convenient way to print the duration a specific code block took to complete. It utilizes [MeasureTime](#measuretime)
and adds a bit of printing around it. You can also pass a different logging function, for instance `logger.debug`.
This especially comes in handy, if your code runs in detached environments (e.g. cronjobs).

```python
import logging
from baumbelt.logs import HuggingLog

logger = logging.getLogger(__name__)

with HuggingLog("cross-compile doom", logging_fn=logger.debug, prefix="[ARM]"):
    # compile hard
    ...

```

This outputs something like:

```
(2629) [DEBUG] 2024-05-28 14:49:51,616 - logging#32 - [ARM]: Start  'cross-compile doom'...
(2629) [DEBUG] 2024-05-28 14:49:53,616 - logging#41 - [ARM]: Finish 'cross-compile doom' in 0:00:02.000204 (2.000204s total)
```

> Vigilant readers may notice the log-origin "logging#32" and "logging#41". These places originate from inside the utility and dont add useful context.
> A way to circumvent this is to pass a lambda:
>
> `with HuggingLog(..., logging_fn=lambda s: logger.debug(s)):`

## group_by_key

`baumbelt.grouping.group_by_key` is a little utility to group a given iterable by an attribute of its items.

```python
from datetime import date
from baumbelt.grouping import group_by_key

iterable = [
    date(2020, 1, 1),
    date(2021, 2, 2),
    date(2022, 3, 3),
    date(2023, 4, 4),
]

grouped = group_by_key(iterable, "weekday")

grouped == {
    1: [date(2021, 2, 2), date(2023, 4, 4)],
    2: [date(2020, 1, 1)],
    3: [date(2022, 3, 3)],
}
```

The passed *attribute_name* can also be a callable (like `date.weekday()`) or just an attribute (like `date.day`).

> There exists `itertools.groupby`, but it would return iterators that may be undesired.

## count_queries [Django]

When developing apps in Django, you often find yourself hunting for performance bottlenecks. Or maybe just
want to get an overview of how many DB calls are actually fired in a certain context. That's what `count_queries` does:

```python
from baumbelt.django.sql import count_queries

with count_queries(name="setup"):
    author, _ = Author.objects.get_or_create(name="Martin Heidegger")
    book, _ = Book.objects.get_or_create(title="Sein und Zeit", author=author)

with count_queries(name="count"):
    num_authors = Author.objects.count()
```

This outputs:

```text
'setup' took 2 / 2 queries
'count' took 1 / 3 queries
```

If you use a multiple database setup, or just don't happen to have your DB named `default`, you can pass
the `db_name` argument to `count_queries`.

## django_sql_debug [Django]

Often it is not just enough to know how many queries are made. You want to know which queries are made exactly and how long each takes. Django offers
to log queries and their runtimes via the `logging` framework. But you often end up with way too much noise.

This is where `django_sql_debug` aims to help. By activating the SQL logs exclusively inside the context manager, you can focus on the queries
you actually want to see.

```python
from baumbelt.django.sql import django_sql_debug

with django_sql_debug():
    author, _ = Author.objects.get_or_create(name="Martin Heidegger")
    book, _ = Book.objects.get_or_create(title="Sein und Zeit", author=author)

```

```text
(0.000) 
SELECT "myapp_author"."id", "myapp_author"."name" FROM "myapp_author" WHERE "myapp_author"."name" = 'Martin Heidegger' LIMIT 21; args=('Martin Heidegger',); alias=default
(0.000) 
SELECT "myapp_book"."id", "myapp_book"."title", "myapp_book"."author_id" FROM "myapp_book" WHERE ("myapp_book"."author_id" = 1 AND "myapp_book"."title" = 'Sein und Zeit') LIMIT 21; args=(1, 'Sein und Zeit'); alias=default
(0.000) 
SELECT COUNT(*) AS "__count" FROM "myapp_author"; args=(); alias=default
```

`django_sql_debug` also accepts some arguments to control how the SQL should be presented:

- `indent`: Boolean to control if the SQL should be reindented. Default is `True`


- `max_arguments`: Integer to control how many arguments in an `IN` clause are displayed. Default is `5`. Set to `-1` to disable argument cutting.
  If there are less than 4 arguments, no truncation is done.


- `truncate_unparsable`: Boolean, default `True`. If a query gets too long to be parsed in reasonable time (for formatting and syntax highlights), we
  will just trim it and display it the default way. So no formatting or colors. But if you really want to see the whole query, you can force that.

In this example, the SQL is indented, and the arguments are limited to 5:

```sql
SELECT "myapp_author"."id",
       "myapp_author"."name"
FROM "myapp_author"
WHERE "myapp_author"."id" IN (0,
                              1,
                              2,
                              3,
    /* 5 truncated */
                              9)
```

## s3utils [Django]

When developing apps in Django, you may find yourself surrounded by AWS storages. In some Django specialities like `collectstatic`, bulk-uploading
makes a lot of sense. `baumbelt.django.s3utils` tries to fill this gap. You can use the storage class `BulkStaticStorage` to enable bulk operations.

### Existence checks

Say, your bucket containing a key `/myfolder/myfile.txt`. When using the base class `S3Boto3Storage`, the following checks:

- exists("myfolder/myfile.txt") -> True
- exists("myfolder/") -> False
- exists("myfolder") -> False
- exists("myfol") -> False

When using the classes from `baumbelt.django.s3utils`, it looks like this:

- exists("myfolder/myfile.txt") -> True
- exists("myfolder/") -> True
- exists("myfolder") -> True
- exists("myfol") -> False

### Example configuration

```python

INSTALLED_APPS = [
    # ...
    "s3utils",
    # ...
]

AWS_PRIVATE_BUCKET = os.environ["AWS_PRIVATE_BUCKET"]
AWS_PUBLIC_BUCKET = os.environ["AWS_PUBLIC_BUCKET"]
PRIVATE_MEDIA_LOCATION = "media"
PUBLIC_MEDIA_LOCATION = "media"
STATIC_LOCATION = "static"
MEDIA_DOMAIN = f"{AWS_PUBLIC_BUCKET}.s3.amazonaws.com"
STATIC_DOMAIN = f"{AWS_PUBLIC_BUCKET}.s3.amazonaws.com"
MEDIA_URL = f"https://{MEDIA_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
STATIC_URL = f"https://{STATIC_DOMAIN}/{STATIC_LOCATION}/"

STORAGES = {
    "default": {"BACKEND": "s3utils.storage.PrivateMediaStorage"},
    "public": {"BACKEND": "s3utils.storage.PublicMediaStorage"},
    "staticfiles": {"BACKEND": "s3utils.storage.BulkStaticStorage"},
}

```

Tip: install [tqdm](https://pypi.org/project/tqdm/) for nice progress bars during uploads.


### wait-for-migrations

When deploying django apps, you may find it necessary to asure that all migrations are done during a step in your deployment. You can use the management command `wait-for-migrations` to do so.
This command blocks the Thread for 60 seconds to handle all migrations of all databases set in `settings.DATABASES`. You can also adjust the timeout value with the argument `--timeout`.