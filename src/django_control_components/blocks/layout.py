"""Layout blocks — arrange other blocks on a page.

The form-schema containers (``Section`` / ``Fieldset`` / ``Tabs`` in
``schemas/layout.py``) stay where they are; those render inside a bound Django
form. These are the page-level equivalents, built on :class:`Block` so they
carry named slots and reach the studio palette.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from ..core.component import setter
from .base import Block

if TYPE_CHECKING:
    from ..core.context import RenderContext

_GAP = {"none": "0", "sm": "0.5rem", "md": "1rem", "lg": "1.5rem", "xl": "2rem"}


def _gap(value: Any, default: str = "md") -> str:
    return _GAP.get(str(value or default), _GAP[default])


class Stack(Block):
    """Vertical flow. ``gap`` is one of none/sm/md/lg/xl."""

    slots = ("default",)
    template_name = "django_control_components/blocks/stack.html"

    @setter
    def gap(self, value: str) -> Self:
        return self._set("gap", value)

    @setter
    def align(self, value: str) -> Self:  # start | center | end | stretch
        return self._set("align", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["gap"] = _gap(self._config.get("gap"))
        data["align"] = self._config.get("align", "stretch")
        return data


class Row(Block):
    """Horizontal flow with wrap / alignment / justification."""

    slots = ("default",)
    template_name = "django_control_components/blocks/row.html"

    @setter
    def gap(self, value: str) -> Self:
        return self._set("gap", value)

    @setter
    def align(self, value: str) -> Self:  # start | center | end | stretch | baseline
        return self._set("align", value)

    @setter
    def justify(self, value: str) -> Self:  # start | center | end | between | around
        return self._set("justify", value)

    @setter
    def wrap(self, value: bool = True) -> Self:
        return self._set("wrap", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        justify = {
            "between": "space-between",
            "around": "space-around",
            "evenly": "space-evenly",
        }.get(self._config.get("justify", "start"), self._config.get("justify", "start"))
        data["gap"] = _gap(self._config.get("gap"))
        data["align"] = self._config.get("align", "stretch")
        data["justify"] = justify
        data["wrap"] = "wrap" if self._config.get("wrap", True) else "nowrap"
        return data


class Grid(Block):
    """A CSS grid — ``cols`` tracks, ``gap`` spacing. Children are usually
    :class:`Column` blocks but need not be."""

    slots = ("default",)
    template_name = "django_control_components/blocks/grid.html"

    @setter
    def cols(self, value: int) -> Self:
        return self._set("cols", value)

    @setter
    def gap(self, value: str) -> Self:
        return self._set("gap", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["cols"] = int(self._config.get("cols", 12))
        data["gap"] = _gap(self._config.get("gap"))
        return data


class Column(Block):
    """A grid child spanning ``span`` tracks (of its parent :class:`Grid`)."""

    slots = ("default",)
    template_name = "django_control_components/blocks/column.html"

    @setter
    def span(self, value: int) -> Self:
        return self._set("span", value)

    @setter
    def offset(self, value: int) -> Self:
        return self._set("offset", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["span"] = int(self._config.get("span", 1))
        data["offset"] = int(self._config.get("offset", 0))
        return data


class Card(Block):
    """A bordered surface with optional header and footer slots."""

    slots = ("header", "body", "footer")
    template_name = "django_control_components/blocks/card.html"

    @setter
    def title(self, value: str) -> Self:
        return self._set("title", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["title"] = self._config.get("title", "")
        return data


class Divider(Block):
    """A horizontal rule. No children."""

    template_name = "django_control_components/blocks/divider.html"


class Spacer(Block):
    """Fixed vertical whitespace. ``size`` is one of none/sm/md/lg/xl."""

    template_name = "django_control_components/blocks/spacer.html"

    @setter
    def size(self, value: str) -> Self:
        return self._set("size", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["size"] = _gap(self._config.get("size"), "lg")
        return data
