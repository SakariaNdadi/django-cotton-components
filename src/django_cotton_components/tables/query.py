"""Turn a validated :class:`TableState` into a queryset.

Security-critical: no querystring value is ever passed to ``order_by`` or
``filter`` as a key. A requested sort must name a column that declared itself
sortable; the ORM path then comes from that column. Search builds a ``Q`` over
the columns that declared themselves searchable, nothing else.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db.models import Q, QuerySet

if TYPE_CHECKING:
    from .columns import Column
    from .filters import Filter
    from .state import TableState


def apply_sort(queryset: QuerySet[Any], state: TableState, columns: list[Column]) -> QuerySet[Any]:
    if not state.sort:
        return queryset
    sortable = {c.name: c for c in columns if c.is_sortable}
    column = sortable.get(state.sort)
    if column is None:
        return queryset
    field = column.sort_field()
    return queryset.order_by(f"-{field}" if state.descending else field)


def apply_search(
    queryset: QuerySet[Any], state: TableState, columns: list[Column]
) -> QuerySet[Any]:
    if not state.search:
        return queryset
    predicate = Q()
    for column in columns:
        if not column.is_searchable:
            continue
        for path in column.search_fields():
            predicate |= Q(**{f"{path}__icontains": state.search})
    if not predicate:
        return queryset
    return queryset.filter(predicate)


def apply_filters(
    queryset: QuerySet[Any], state: TableState, filters: list[Filter]
) -> QuerySet[Any]:
    by_name = {f.name: f for f in filters}
    for name, raw in state.filters.items():
        f = by_name.get(name)
        if f is not None:
            queryset = f.apply(queryset, raw)
    return queryset


def apply_all(
    queryset: QuerySet[Any],
    state: TableState,
    columns: list[Column],
    filters: list[Filter],
) -> QuerySet[Any]:
    queryset = apply_filters(queryset, state, filters)
    queryset = apply_search(queryset, state, columns)
    queryset = apply_sort(queryset, state, columns)
    return queryset
