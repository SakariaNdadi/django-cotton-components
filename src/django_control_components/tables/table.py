from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.utils.safestring import SafeString

from .. import htmx as htmx_adapter
from ..conf import dcc_settings
from ..core.context import RenderContext
from . import cursor, query
from .state import TableState

if TYPE_CHECKING:
    from django.http import HttpRequest

    from ..actions.action import Action
    from .columns import Column
    from .filters import Filter


class Table:
    shell_template = "django_control_components/tables/table.html"
    content_template = "django_control_components/tables/_content.html"

    def __init__(self, queryset: QuerySet[Any]) -> None:
        self._queryset = queryset
        self._columns: list[Column] = []
        self._filters: list[Filter] = []
        self._row_actions: list[Action] = []
        self._bulk_actions: list[Action] = []
        self._config: dict[str, Any] = {}

    @classmethod
    def make(cls, queryset: QuerySet[Any]) -> Self:
        return cls(queryset)

    # -- configuration ---------------------------------------------

    def columns(self, columns: list[Column]) -> Self:
        self._columns = list(columns)
        return self

    def filters(self, filters: list[Filter]) -> Self:
        self._filters = list(filters)
        return self

    def actions(self, actions: list[Action]) -> Self:
        self._row_actions = list(actions)
        return self

    def bulk_actions(self, actions: list[Action]) -> Self:
        self._bulk_actions = list(actions)
        return self

    def record_url(self, value: str | Any) -> Self:
        """Clicking anywhere on a row (bar its buttons/inputs) navigates to
        ``value(record)`` - a full page."""
        self._config["record_url"] = value
        return self

    def record_action(self, action: Action) -> Self:
        """Clicking a row fires this Action - typically ``.modal(...)`` for a
        detail dialog, or ``.to_url(...)`` to navigate. Registered like a row
        action but never shown as a column button."""
        self._config["record_action"] = action
        return self

    def record_preview(self, value: Any) -> Self:
        """Show a hover card with extra record info. ``value(record)`` returns
        HTML (use ``format_html``)."""
        self._config["record_preview"] = value
        return self

    def id(self, value: str) -> Self:
        self._config["id"] = value
        return self

    def default_sort(self, field: str) -> Self:
        self._config["default_sort"] = field
        return self

    def paginate(self, choices: list[int]) -> Self:
        self._config["per_page_choices"] = choices
        return self

    def searchable(self, value: bool = True) -> Self:
        self._config["searchable"] = value
        return self

    def client_side(self) -> Self:
        self._config["mode"] = "client"
        return self

    def server_side(self, *, strategy: str | None = None) -> Self:
        self._config["mode"] = "server"
        if strategy is not None:
            self._config["page_strategy"] = strategy
        return self

    def page_numbers(self) -> Self:
        """Classic numbered pagination (one ``COUNT(*)`` per render)."""
        self._config["page_strategy"] = "pages"
        return self

    def stream(self) -> Self:
        """Keyset pagination + append-on-scroll - safe over millions of rows."""
        self._config["page_strategy"] = "more"
        return self

    def load_more_button(self) -> Self:
        self._config["load_more_trigger"] = "click"
        return self

    def empty_message(self, text: str) -> Self:
        self._config["empty_message"] = text
        return self

    def presentation(self, value: str) -> Self:
        """``"grid"`` (default) renders a table; ``"feed"`` renders a borderless
        list - for compact dashboard cards."""
        self._config["presentation"] = value
        return self

    def pagination_position(self, value: str) -> Self:
        """``"left"`` | ``"center"`` | ``"right"`` (default)."""
        self._config["pagination_position"] = value
        return self

    def infinite_scroll(self) -> Self:
        """Append rows on scroll instead of showing a pager."""
        self._config["infinite_scroll"] = True
        return self

    def _page_strategy(self) -> str:
        if self._config.get("infinite_scroll"):
            return "more"
        return self._config.get("page_strategy", "more")

    # -- introspection ------------------------------------------

    @property
    def table_id(self) -> str:
        return self._config.get("id") or self._queryset.model._meta.model_name or "table"

    @property
    def key(self) -> str:
        return f"table-{self.table_id}"

    @property
    def content_target(self) -> str:
        return f"#{self.table_id}-content"

    # -- ActionOwner protocol ------------------------------------

    @property
    def _all_actions(self) -> list[Action]:
        extra = [self._config["record_action"]] if "record_action" in self._config else []
        return [*self._row_actions, *self._bulk_actions, *extra]

    def get_actions(self) -> dict[str, Any]:
        out = {}
        for action in self._all_actions:
            action.bind_owner(self.key)
            out[action.name] = action
        return out

    def get_action_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        state = self._default_state(request)
        return query.apply_all(self._queryset, state, self._columns, self._filters)

    def _register(self) -> None:
        if self._all_actions:
            from ..actions.registry import registry

            self.get_actions()  # binds owner key onto each action
            registry.register(self)

    @property
    def per_page_choices(self) -> list[int]:
        return self._config.get("per_page_choices") or list(dcc_settings.TABLE_PER_PAGE_CHOICES)

    def _default_state(self, request: HttpRequest | None) -> TableState:
        params = request.GET if request is not None else _empty_query()
        state = TableState.from_query(self.table_id, params)
        if state.sort is None and self._config.get("default_sort"):
            raw = self._config["default_sort"]
            state.descending = raw.startswith("-")
            state.sort = raw[1:] if state.descending else raw
        state.per_page = state.per_page or self.per_page_choices[0]
        return state

    def _resolve_mode(self, request: HttpRequest | None) -> str:
        forced = self._config.get("mode")
        if forced:
            return forced
        max_rows = dcc_settings.TABLE_CLIENT_SIDE_MAX_ROWS
        probe = len(self._queryset.values_list("pk", flat=True)[: max_rows + 1])
        return "client" if probe <= max_rows else "server"

    # -- rendering --------------------------------------------

    def _base_path(self, request: HttpRequest | None) -> str:
        return request.path if request is not None else ""

    def _swap(self, request: HttpRequest | None, params: str) -> Any:
        path = self._base_path(request)
        marker = f"_dcc_table={self.table_id}"
        query = f"{params}&{marker}" if params else marker
        return htmx_adapter.get(
            f"{path}?{query}",
            target=self.content_target,
            swap="outerHTML",
            push_url=f"{path}?{params}" if params else path,
            indicator=f".dcc-table#{self.table_id}",
        )

    def _rows_payload(self, records: list[Any], ctx: RenderContext) -> list[dict[str, Any]]:
        from django.utils.html import strip_tags

        payload = []
        for record in records:
            row: dict[str, Any] = {"_pk": str(getattr(record, "pk", ""))}
            for i, column in enumerate(self._columns):
                row[str(i)] = strip_tags(column.cell_text(record, ctx)).strip()
            payload.append(row)
        return payload

    def _row_attrs(self, record: Any, request: HttpRequest | None) -> str:
        from django.forms.utils import flatatt

        from ..core.evaluate import evaluate

        data: dict[str, str] = {}
        url_fn = self._config.get("record_url")
        if url_fn is not None:
            resolved = evaluate(url_fn, RenderContext(request=request, record=record))
            if resolved:
                data["data-dcc-href"] = str(resolved)
        action = self._config.get("record_action")
        if action is not None and not data:
            data.update(action.row_click_attrs(record=record, request=request))
        return flatatt(data) if data else ""

    def _row_preview(self, record: Any, request: HttpRequest | None) -> str:
        from ..core.evaluate import evaluate

        fn = self._config.get("record_preview")
        if fn is None:
            return ""
        html = evaluate(fn, RenderContext(request=request, record=record))
        return str(html) if html else ""

    def _rendered_rows(self, records: list[Any], ctx: RenderContext) -> list[dict[str, Any]]:
        request = ctx.request
        inline_actions = [a for a in self._row_actions if not a.is_collapsed]
        collapsed_actions = [a for a in self._row_actions if a.is_collapsed]
        rows = []
        for record in records:
            triggers = [
                t for a in inline_actions if (t := a.render_trigger(record=record, request=request))
            ]
            if collapsed_actions:
                items = [
                    t
                    for a in collapsed_actions
                    if (t := a.render_trigger(record=record, request=request))
                ]
                if items:
                    from ..ui import Menu

                    triggers.append(
                        Menu.make()
                        .items(items)
                        .render(RenderContext(request=request, record=record))
                    )
            rows.append(
                {
                    "pk": getattr(record, "pk", ""),
                    "record": record,
                    "cells": [c.render_cell(record, ctx) for c in self._columns],
                    "action_triggers": triggers,
                    "row_attrs": SafeString(self._row_attrs(record, request)),
                    "preview_html": SafeString(self._row_preview(record, request)),
                }
            )
        return rows

    def _headers(
        self, request: HttpRequest | None, state: TableState, mode: str
    ) -> list[dict[str, Any]]:
        out = []
        for column in self._columns:
            entry: dict[str, Any] = {
                "label": column.header,
                "name": column.name,
                "sortable": column.is_sortable,
                "sorted": "asc"
                if state.sort == column.name and not state.descending
                else "desc"
                if state.sort == column.name
                else "",
            }
            if column.is_sortable and mode == "server":
                entry["htmx"] = self._swap(request, state.toggled_sort(column.name))
            out.append(entry)
        return out

    def _pagination(
        self, request: HttpRequest | None, state: TableState, page: Any
    ) -> list[dict[str, Any]]:
        links = []
        if page.has_previous():
            prev = TableState(**{**state.__dict__, "page": page.previous_page_number()})
            links.append({"label": "Previous", "htmx": self._swap(request, prev.to_params())})
        links.append(
            {"label": f"Page {page.number} of {page.paginator.num_pages}", "current": True}
        )
        if page.has_next():
            nxt = TableState(**{**state.__dict__, "page": page.next_page_number()})
            links.append({"label": "Next", "htmx": self._swap(request, nxt.to_params())})
        return links

    def _content_context(
        self, request: HttpRequest | None, state: TableState, mode: str
    ) -> dict[str, Any]:
        ctx = RenderContext(request=request)
        qs = query.apply_all(self._queryset, state, self._columns, self._filters)
        has_bulk = bool(self._bulk_actions)
        per_page = state.per_page or self.per_page_choices[0]
        infinite_scroll = bool(self._config.get("infinite_scroll"))
        # Only offer a "rows per page" picker when the developer explicitly passed
        # >1 choice via .paginate([...]); otherwise the first choice is a fixed
        # page size (10 by default).
        explicit_choices = self._config.get("per_page_choices") or []
        show_per_page = not infinite_scroll and len(explicit_choices) > 1

        per_page_htmx = None
        if show_per_page and mode == "server":
            base = f"{self._base_path(request)}?_dcc_table={self.table_id}"
            carried = state.to_params(per_page=None, page=None, after=None)
            per_page_htmx = htmx_adapter.get(
                f"{base}&{carried}" if carried else base,
                target=self.content_target,
                swap="outerHTML",
                push_url=self._base_path(request),
                trigger="change",
            )

        common = {
            "table_id": self.table_id,
            "mode": mode,
            "headers": self._headers(request, state, mode),
            "column_count": len(self._columns)
            + (1 if self._row_actions else 0)
            + (1 if has_bulk else 0),
            "row_actions": self._row_actions,
            "has_bulk": has_bulk,
            "empty_message": self._config.get("empty_message", "No results."),
            "presentation": self._config.get("presentation", "grid"),
            "pagination_position": self._config.get("pagination_position", "right"),
            "infinite_scroll": infinite_scroll,
            "per_page": per_page,
            "per_page_choices": self.per_page_choices,
            "per_page_param": f"t_{self.table_id}_per_page",
            "show_per_page": show_per_page,
            "per_page_htmx": per_page_htmx,
            "bulk_action_triggers": [a.render_trigger(request=request) for a in self._bulk_actions],
        }

        if mode == "client":
            records = list(qs)
            return {
                **common,
                "rows": self._rendered_rows(records, ctx),
                "client_config": {
                    "rows": self._rows_payload(records, ctx),
                    "perPage": per_page,
                    "infiniteScroll": infinite_scroll,
                },
                "config_id": f"{self.table_id}-config",
            }

        if self._page_strategy() == "pages":
            paginator = Paginator(qs, per_page)
            page = paginator.get_page(state.page)
            return {
                **common,
                "rows": self._rendered_rows(list(page.object_list), ctx),
                "pagination": self._pagination(request, state, page),
            }

        # keyset / append-on-scroll - no COUNT, no OFFSET
        sort_field, descending = self._effective_sort(state)
        records, next_token = cursor.paginate(
            qs,
            sort_field=sort_field,
            descending=descending,
            after=state.after,
            per_page=per_page,
        )
        return {
            **common,
            "rows": self._rendered_rows(records, ctx),
            "load_more_htmx": self._load_more(request, state, next_token),
            "load_more_label": "Load more"
            if self._config.get("load_more_trigger") == "click"
            else "",
        }

    def _effective_sort(self, state: TableState) -> tuple[str, bool]:
        sortable = {c.name: c for c in self._columns if c.is_sortable}
        column = sortable.get(state.sort or "")
        if column is not None:
            return column.sort_field(), state.descending
        return "pk", state.descending

    def _load_more(
        self, request: HttpRequest | None, state: TableState, next_token: str | None
    ) -> Any:
        if not next_token:
            return None
        nxt = TableState(**{**state.__dict__, "after": next_token})
        path = self._base_path(request)
        params = f"{nxt.to_params()}&_dcc_table={self.table_id}&_dcc_rows=1"
        trigger = self._config.get("load_more_trigger", "revealed")
        return htmx_adapter.get(
            f"{path}?{params}",
            target="this",
            swap="outerHTML",
            trigger=trigger,
        )

    def render_content(self, request: HttpRequest | None = None) -> SafeString:
        self._register()
        state = self._default_state(request)
        mode = self._resolve_mode(request)
        data = self._content_context(request, state, mode)
        rows_only = request is not None and request.GET.get("_dcc_rows") == "1"
        template = (
            "django_control_components/tables/_rows.html" if rows_only else self.content_template
        )
        return SafeString(render_to_string(template, data, request=request))

    def render(self, request: HttpRequest | None = None) -> SafeString:
        self._register()
        state = self._default_state(request)
        mode = self._resolve_mode(request)
        searchable = self._config.get("searchable", any(c.is_searchable for c in self._columns))

        marked_path = f"{self._base_path(request)}?_dcc_table={self.table_id}"

        # Server mode: search round-trips on keyup. Client mode keeps search
        # local (the rows are already in the page).
        toolbar_htmx = None
        if mode == "server" and searchable:
            toolbar_htmx = htmx_adapter.get(
                marked_path,
                target=self.content_target,
                swap="outerHTML",
                push_url=self._base_path(request),
                trigger="keyup changed delay:300ms, search",
            )

        # Filters always round-trip in both modes (client-side value/display
        # equality is unreliable, esp. for boolean columns) and must carry the
        # _dcc_table marker so the mixin returns the fragment, not the whole page.
        filter_htmx = None
        if self._filters:
            filter_htmx = htmx_adapter.get(
                marked_path,
                target=self.content_target,
                swap="outerHTML",
                push_url=self._base_path(request),
                trigger="change",
            )

        # After an action mutates data the endpoint fires HX-Trigger dcc:refresh;
        # re-fetch this table's content fragment in place (works in both modes).
        refresh_htmx = None
        if self._all_actions:
            path = self._base_path(request)
            marker = f"_dcc_table={self.table_id}"
            refresh_htmx = htmx_adapter.get(
                f"{path}?{marker}",
                target=self.content_target,
                swap="outerHTML",
                trigger="dcc:refresh from:body",
            )

        data = {
            "table_id": self.table_id,
            "mode": mode,
            "searchable": searchable,
            "search": state.search,
            "search_param": f"t_{self.table_id}_search",
            "filters": [
                {
                    "name": f.name,
                    "param": f"t_{self.table_id}_f_{f.name}",
                    "header": f.header,
                    "choices": f.choices(),
                    "value": state.filters.get(f.name, ""),
                }
                for f in self._filters
            ],
            "toolbar_htmx": toolbar_htmx,
            "filter_htmx": filter_htmx,
            "refresh_htmx": refresh_htmx,
            "owner_key_slug": self.key,
            "has_actions": bool(self._all_actions),
            "has_bulk": bool(self._bulk_actions),
            "content_html": self.render_content(request),
        }
        return SafeString(render_to_string(self.shell_template, data, request=request))


def _empty_query() -> Any:
    from django.http import QueryDict

    return QueryDict()
