"""View mixin for table pages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import HttpResponse

from .. import htmx

if TYPE_CHECKING:
    from .table import Table


class TableMixin:
    """Render a :class:`Table` and answer htmx partial-swap requests.

    Set ``table`` or override ``get_table()``. On an ``HX-Request`` carrying the
    table's marker the mixin returns only the content fragment; otherwise the
    full page renders and the table appears via ``{{ table_html }}``.

    Place this mixin *before* any auth mixin so ``dispatch`` still runs the auth
    check first (the partial is served from ``get``, after ``dispatch``).
    """

    table: Table | None = None
    table_context_name = "table_html"

    def get_table(self) -> Table:
        if self.table is None:
            raise ValueError(f"{type(self).__name__} needs a `table` or `get_table()`")
        return self.table

    def get(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        table = self.get_table()
        if htmx.is_htmx(request) and request.GET.get("_dcc_table") == table.table_id:
            return HttpResponse(table.render_content(request))
        return super().get(request, *args, **kwargs)  # type: ignore[misc]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context_data(**kwargs)  # type: ignore[misc]
        context[self.table_context_name] = self.get_table().render(self.request)  # type: ignore[attr-defined]
        return context
