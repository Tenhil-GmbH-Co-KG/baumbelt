from typing import Iterator

from django.db.models import QuerySet


def batch_ordered_queryset(queryset: QuerySet, batch_size: int, ordered_field: str = "pk") -> Iterator[list]:
    last_value = None

    assert "pk" in queryset.query.order_by, (
        f"QuerySets have to be ordered by primary key, got {queryset.query.order_by}"
    )

    while True:
        work_qs = queryset
        if last_value is not None:
            work_qs = queryset.filter(**{f"{ordered_field}__gt": last_value})

        _batch = list(work_qs[:batch_size])
        if len(_batch) == 0:
            break

        last_item = _batch[-1]
        if isinstance(last_item, tuple):  # support `.values_list` on the queryset. Assumes "pk" is first field.
            last_value = last_item[0]
        else:
            last_value = _batch[-1].pk

        yield _batch

        if len(_batch) < batch_size:
            break


def iterate_batch_ordered_queryset(queryset: QuerySet, batch_size: int, ordered_field: str = "pk") -> Iterator:
    for batch in batch_ordered_queryset(queryset=queryset, batch_size=batch_size, ordered_field=ordered_field):
        for item in batch:
            yield item
