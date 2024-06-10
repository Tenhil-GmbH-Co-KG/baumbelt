# baumbelt

Curated collection of handy utility functions for Python by the Tenhil GmbH.

# Installation

Run `pip install baumbelt`

# Utilities

## EnumContainsMeta

`baumbelt.enum.EnumContainsMeta` offers a metaclass, that adds the syntactic sugar of member checks. The default `Enum` only allows checks for values:

```python
from enum import Enum
from baumbelt.enum import EnumContainsMeta


class AtomEnum(Enum, metaclass=EnumContainsMeta):
    hydrogen = 1
    helium = 2


"hydrogen" in AtomEnum  # True
2 in AtomEnum  # True
"water" in AtomEnum  # False
```

## MeasureTime

The `baumbelt.time.MeasureTime` class can be used as a context manager to have a syntactically nice way to measure the time a block of code takes.
The following two snippets produce the same result.

Vanilla:

```python
from datetime import datetime

t0 = datetime.now()
this_call_takes_a_while()
tend = datetime.now() - t0

print(f"{tend} ({tend.total_seconds()}s)")
```

and with `MeasureTime`:

```python
from baumbelt.time import MeasureTime

with MeasureTime() as mt:
    this_call_takes_a_while()
    print(mt)
```

## Timer
`baumbelt.time.timer` is a more flexible utility compared to `MeasureTime`. It additionally allows to *tap* the current time.\
This snippet:

```python
def fetch_raw_data():
    with Timer("fetch_raw_data") as t:
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
v'main' started...
  v'fetch_raw_data' started...
    > 'got users'                              took 0.8002s (at 0.8002s)
    > 'got events'                             took 2.0003s (at 2.8005s)
  ʌ'fetch_raw_data' took 3.3008s
  > 'enriching..'                            took 3.3009s (at 3.3009s)
  v'enrich_data' started...
    > 'enriched-step-1'                        took 100.1561ms (at 100.1561ms)
    > 'enriched-step-2'                        took 20.1433ms (at 120.2993ms)
  ʌ'enrich_data' took 120.3260ms
ʌ'main' took 3.4212s
```


## HuggingLog

`baumbelt.logging.HuggingLog` offers a convenient way to print the duration a specific code block took. It utilizes [MeasureTime](#measuretime) and adds a bit of printing around it. You can also pass
a different logging function, for instance `logger.debug`. This comes especially comes in handy, if you run in detached environment (eg: cronjob).

```python
from baumbelt.logging import HuggingLog
import logging

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

> Vigilant readers may notice the log-origin "logging#32" and "logging#41". These origins are from inside the utility and probably not very useful. You can circumvent this by passing a lambda:
>
> `with HuggingLog(..., logging_fn=lambda s: logger.debug(s)):`

## group_by_key

`baumbelt.grouping.group_by_key` is a little utility to group a given iterable by an attribute of its items.

```python
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

> There exists `itertools.groupby`, but it would return iterators that may are undesired.
