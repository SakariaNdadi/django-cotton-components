from __future__ import annotations

from typing import Any, Self

from django.utils.safestring import SafeString

from ..core.component import Component, setter
from ..core.context import RenderContext
from ..icons import render_icon


class Menu(Component):
    """An Alpine disclosure: a trigger button and a list of pre-rendered items.

    Items are HTML strings (usually rendered :class:`Button`/link triggers) so a
    row can collapse several actions behind one "⋯".
    """

    template_name = "django_cotton_components/ui/menu.html"

    @setter
    def label(self, value: str) -> Self:
        return self._set("label", value)

    @setter
    def icon(self, value: str) -> Self:
        return self._set("icon", value)

    @setter
    def items(self, value: list[SafeString | str]) -> Self:
        return self._set("items", list(value))

    @setter
    def align(self, value: str) -> Self:
        return self._set("align", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["attrs"].add_class("dcc-menu")
        data["label"] = self.resolve("label", ctx) or ""
        data["icon_html"] = render_icon(self.resolve("icon", ctx) or "ellipsis-vertical")
        data["items"] = self._config.get("items", [])
        data["align"] = self._config.get("align", "end")
        return data
