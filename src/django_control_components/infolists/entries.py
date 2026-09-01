"""Read-only counterparts to schema fields.

An entry pulls a value off ``ctx.record`` and renders it - no form, no input.
Layout reuses ``Section`` / ``Grid`` from :mod:`schemas.layout`.
"""

from __future__ import annotations

from typing import Any, Self

from django.utils.dateformat import format as date_format
from django.utils.text import capfirst
from django.utils.timesince import timesince

from ..core.component import UNSET, Component, setter
from ..core.context import RenderContext
from ..core.evaluate import evaluate
from ..core.paths import traverse


class Entry(Component):
    template_name = "django_control_components/infolists/entry.html"

    @setter
    def label(self, value: str) -> Self:
        return self._set("label", value)

    @setter
    def state(self, fn: Any) -> Self:
        return self._set("state_fn", fn)

    @setter
    def placeholder(self, value: str) -> Self:
        return self._set("placeholder", value)

    @property
    def header(self) -> str:
        configured = self._config.get("label", UNSET)
        if configured is not UNSET:
            return configured
        return capfirst((self._name or "").replace("_", " ").replace(".", " "))

    def raw_value(self, ctx: RenderContext) -> Any:
        state_fn = self._config.get("state_fn")
        if state_fn is not None:
            return evaluate(state_fn, ctx.child(record=ctx.record))
        return traverse(ctx.record, self._name or "")

    def display(self, ctx: RenderContext) -> Any:
        value = self.raw_value(ctx)
        if value in (None, ""):
            return self._config.get("placeholder", "-")
        return value

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["label"] = self.header
        data["value"] = self.display(ctx)
        data["kind"] = "text"
        return data


class TextEntry(Entry):
    pass


class BadgeEntry(Entry):
    @setter
    def colors(self, mapping: dict[str, str]) -> Self:
        return self._set("colors", mapping)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["kind"] = "badge"
        colors = self._config.get("colors") or {}
        data["variant"] = colors.get(str(self.raw_value(ctx)), "")
        return data


class BooleanEntry(Entry):
    def display(self, ctx: RenderContext) -> Any:
        return "Yes" if self.raw_value(ctx) else "No"

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["kind"] = "badge"
        data["variant"] = "success" if self.raw_value(ctx) else ""
        return data


class DateEntry(Entry):
    @setter
    def since(self, value: bool = True) -> Self:
        return self._set("since", value)

    @setter
    def date_format(self, fmt: str) -> Self:
        return self._set("date_format", fmt)

    def display(self, ctx: RenderContext) -> Any:
        value = self.raw_value(ctx)
        if not value:
            return self._config.get("placeholder", "-")
        if self._config.get("since"):
            return f"{timesince(value)} ago"
        return date_format(value, self._config.get("date_format", "N j, Y"))
