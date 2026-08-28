"""Table columns.

A column knows how to (a) label its header, (b) pull a display value from a
record, and (c) declare — separately — the ORM path used for sorting and the
paths used for search. Query params never reach the ORM: the table looks a
requested sort key up in the set of sortable column names and then uses
``column.sort_field()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from django.utils.dateformat import format as date_format
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe
from django.utils.text import capfirst
from django.utils.timesince import timesince

from ..core.component import UNSET, setter
from ..core.evaluate import evaluate

if TYPE_CHECKING:
    from ..core.context import RenderContext


class Column:
    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self._config: dict[str, Any] = {}
        self._apply_kwargs(kwargs)

    @classmethod
    def make(cls, name: str, **kwargs: Any) -> Self:
        return cls(name, **kwargs)

    def _apply_kwargs(self, kwargs: dict[str, Any]) -> None:
        for key, value in kwargs.items():
            method = getattr(type(self), key, None)
            if method is None or not getattr(method, "__dcc_setter__", False):
                valid = sorted(
                    n
                    for n in dir(type(self))
                    if getattr(getattr(type(self), n, None), "__dcc_setter__", False)
                )
                raise TypeError(f"{type(self).__name__} has no setter {key!r}. Valid: {valid}")
            getattr(self, key)(value)

    def _set(self, key: str, value: Any) -> Self:
        self._config[key] = value
        return self

    # -- setters -----------------------------------------------------

    @setter
    def label(self, value: str) -> Self:
        return self._set("label", value)

    @setter
    def sortable(self, sort_field: str | bool = True) -> Self:
        return self._set("sortable", sort_field)

    @setter
    def searchable(self, search_fields: list[str] | bool = True) -> Self:
        return self._set("searchable", search_fields)

    @setter
    def align(self, value: str) -> Self:
        return self._set("align", value)

    @setter
    def limit(self, chars: int) -> Self:
        return self._set("limit", chars)

    @setter
    def allow_html(self, value: bool = True) -> Self:
        return self._set("allow_html", value)

    @setter
    def state(self, fn: Any) -> Self:
        """Override the displayed value: ``lambda record: ...``."""
        return self._set("state_fn", fn)

    # -- introspection --------------------------------------------

    @property
    def header(self) -> str:
        configured = self._config.get("label", UNSET)
        if configured is not UNSET:
            return configured
        return capfirst(self.name.replace("_", " ").replace(".", " "))

    @property
    def is_sortable(self) -> bool:
        return "sortable" in self._config

    @property
    def is_searchable(self) -> bool:
        return "searchable" in self._config

    def sort_field(self) -> str:
        configured = self._config.get("sortable", True)
        if isinstance(configured, str):
            return configured
        return self.name.replace(".", "__")

    def search_fields(self) -> list[str]:
        configured = self._config.get("searchable", True)
        if isinstance(configured, list):
            return configured
        return [self.name.replace(".", "__")]

    # -- value extraction -------------------------------------

    def get_value(self, record: Any, ctx: RenderContext) -> Any:
        state_fn = self._config.get("state_fn")
        if state_fn is not None:
            return evaluate(state_fn, ctx.child(record=record))
        value: Any = record
        for part in self.name.split("."):
            if value is None:
                return None
            value = getattr(value, part, None)
            if callable(value):
                value = value()
        return value

    def render_cell(self, record: Any, ctx: RenderContext) -> SafeString:
        value = self.get_value(record, ctx)
        return self.format(value)

    def format(self, value: Any) -> SafeString:
        if value is None:
            return SafeString("")
        text = str(value)
        limit = self._config.get("limit")
        if limit and len(text) > limit:
            text = text[:limit].rstrip() + "…"
        if self._config.get("allow_html"):
            return mark_safe(text)  # noqa: S308  -- documented opt-in
        return format_html("{}", text)

    def cell_text(self, record: Any, ctx: RenderContext) -> str:
        """Plain string for client-side mode's JSON payload."""
        return str(self.render_cell(record, ctx))


class TextColumn(Column):
    pass


class BooleanColumn(Column):
    @setter
    def labels(self, mapping: tuple[str, str]) -> Self:
        return self._set("labels", mapping)

    def format(self, value: Any) -> SafeString:
        yes, no = self._config.get("labels", ("Yes", "No"))
        return format_html('<span class="dcc-badge">{}</span>', yes if value else no)


class BadgeColumn(Column):
    @setter
    def colors(self, mapping: dict[str, str]) -> Self:
        return self._set("colors", mapping)

    def format(self, value: Any) -> SafeString:
        if value is None:
            return SafeString("")
        return format_html('<span class="dcc-badge">{}</span>', str(value))


class DateColumn(Column):
    @setter
    def date_format(self, fmt: str) -> Self:
        return self._set("date_format", fmt)

    @setter
    def since(self, value: bool = True) -> Self:
        return self._set("since", value)

    def format(self, value: Any) -> SafeString:
        if value is None:
            return SafeString("")
        if self._config.get("since"):
            return format_html("{}", f"{timesince(value)} ago")
        fmt = self._config.get("date_format", "N j, Y")
        return format_html("{}", date_format(value, fmt))


class ImageColumn(Column):
    @setter
    def thumbnail(self, size: tuple[int, int]) -> Self:
        return self._set("thumbnail", size)

    @setter
    def rounded(self, value: bool = True) -> Self:
        return self._set("rounded", value)

    def format(self, value: Any) -> SafeString:
        if not value:
            return SafeString("")
        width, height = self._config.get("thumbnail", (48, 48))
        url = getattr(value, "url", "")
        if self._config.get("thumbnail"):
            try:
                from ..images.backends import get_thumbnail_backend

                url = get_thumbnail_backend().thumbnail(value, width, height)
            except Exception:
                url = getattr(value, "url", "")
        cls = "dcc-image-thumb" + (" dcc-image-thumb--round" if self._config.get("rounded") else "")
        return format_html(
            '<img class="{}" src="{}" width="{}" height="{}" alt="" loading="lazy">',
            cls,
            url,
            width,
            height,
        )

    def cell_text(self, record: Any, ctx: RenderContext) -> str:
        value = self.get_value(record, ctx)
        return getattr(value, "url", "") or ""
