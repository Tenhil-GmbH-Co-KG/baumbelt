from collections import defaultdict
from typing import Iterable


def group_by_key(items: Iterable, attribute_name: str) -> dict:
    """
    For a given iterable, returns a dict where each key points to a list
    of items, identified by the passed `attribute_name`.

    Equivalent to:

    ```
    groups = defaultdict(list)
    for item in items:
        groups[item.attribute_name].append(item)
    ```
    """

    grouped = defaultdict(list)
    for item in items:
        attribute = getattr(item, attribute_name)
        if callable(attribute):
            attribute = attribute()
        grouped[attribute].append(item)

    return dict(grouped)
