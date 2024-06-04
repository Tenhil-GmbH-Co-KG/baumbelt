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

