"""Parse a table's slice of the querystring.

Every key is namespaced by the table id (``t_<id>_sort`` etc.) so two tables
render on one page without colliding. Nothing parsed here is trusted — the
table validates each value against its own columns/filters before use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlencode

if TYPE_CHECKING:
    from django.http import QueryDict


@dataclass
class TableState:
    table_id: str
    sort: str | None = None
    descending: bool = False
    search: str = ""
    page: int = 1
    per_page: int | None = None
    after: str | None = None
    filters: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_query(cls, table_id: str, query: QueryDict) -> TableState:
        prefix = f"t_{table_id}_"
        raw_sort = query.get(prefix + "sort", "")
        descending = raw_sort.startswith("-")
        sort = raw_sort[1:] if descending else raw_sort or None

        try:
            page = max(1, int(str(query.get(prefix + "page", "1"))))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page: int | None = int(str(query[prefix + "per_page"]))
        except (KeyError, TypeError, ValueError):
            per_page = None

        filters: dict[str, str] = {
            str(key)[len(prefix) + 2 :]: str(value)
            for key, value in query.items()
            if str(key).startswith(prefix + "f_") and value != ""
        }
        return cls(
            table_id=table_id,
            sort=sort,
            descending=descending,
            search=query.get(prefix + "search", "").strip(),
            page=page,
            per_page=per_page,
            after=query.get(prefix + "after") or None,
            filters=filters,
        )

    def _prefix(self) -> str:
        return f"t_{self.table_id}_"

    def to_params(self, **overrides: object) -> str:
        p = self._prefix()
        params: dict[str, str] = {}
        if self.sort:
            params[p + "sort"] = ("-" if self.descending else "") + self.sort
        if self.search:
            params[p + "search"] = self.search
        if self.page > 1:
            params[p + "page"] = str(self.page)
        if self.per_page:
            params[p + "per_page"] = str(self.per_page)
        if self.after:
            params[p + "after"] = self.after
        for name, fvalue in self.filters.items():
            params[p + "f_" + name] = fvalue
        for key, override in overrides.items():
            full = p + key
            if override in (None, "", 1):
                params.pop(full, None)
            else:
                params[full] = str(override)
        return urlencode(params)

    def toggled_sort(self, column_name: str) -> str:
        """Params string for clicking a column header."""
        if self.sort == column_name and not self.descending:
            return self.to_params(sort=f"-{column_name}", page=None, after=None)
        if self.sort == column_name and self.descending:
            return self.to_params(sort=None, page=None, after=None)
        return self.to_params(sort=column_name, page=None, after=None)
