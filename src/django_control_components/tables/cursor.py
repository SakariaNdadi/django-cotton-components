"""Keyset (cursor) pagination.

Deep OFFSET and ``SELECT COUNT(*)`` both scale badly. Keyset pagination orders
by ``(sort_column, pk)`` and asks for "the page after this (value, pk)". No
count, no offset - each page is one indexed range scan.

The cursor token is an opaque base64 of ``[sort_value, pk]``; it never carries a
column name or ORM path, so a tampered token can at worst point at a wrong row
in the *already-scoped* queryset.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from django.db.models import Q, QuerySet


def encode(sort_value: Any, pk: Any) -> str:
    raw = json.dumps([_jsonable(sort_value), _jsonable(pk)], separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode(token: str | None) -> tuple[Any, Any] | None:
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        value, pk = json.loads(raw)
    except (ValueError, binascii.Error):
        return None
    return value, pk


def _jsonable(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def paginate(
    queryset: QuerySet[Any],
    *,
    sort_field: str,
    descending: bool,
    after: str | None,
    per_page: int,
) -> tuple[list[Any], str | None]:
    """Return ``(rows, next_token)`` - ``next_token`` is ``None`` at the end.

    Fetches ``per_page + 1`` rows to know whether another page exists without a
    count.
    """
    ordering = [f"-{sort_field}", "-pk"] if descending else [sort_field, "pk"]
    queryset = queryset.order_by(*ordering)

    cursor = decode(after)
    if cursor is not None:
        value, pk = cursor
        if descending:
            queryset = queryset.filter(
                Q(**{f"{sort_field}__lt": value}) | (Q(**{sort_field: value}) & Q(pk__lt=pk))
            )
        else:
            queryset = queryset.filter(
                Q(**{f"{sort_field}__gt": value}) | (Q(**{sort_field: value}) & Q(pk__gt=pk))
            )

    rows = list(queryset[: per_page + 1])
    if len(rows) <= per_page:
        return rows, None
    rows = rows[:per_page]
    last = rows[-1]
    field_value = _resolve(last, sort_field)
    return rows, encode(field_value, last.pk)


def _resolve(obj: Any, path: str) -> Any:
    for part in path.split("__"):
        obj = getattr(obj, part, None)
        if obj is None:
            break
    return obj
