from __future__ import annotations

from typing import Any, Self

from ..core.component import Component, setter
from ..core.context import RenderContext


class Badge(Component):
    """A small status pill. ``variant`` (or a colour key) drives the modifier class."""

    template_name = "django_cotton_components/ui/badge.html"

    @setter
    def label(self, value: str) -> Self:
        return self._set("label", value)

    @setter
    def variant(self, value: str) -> Self:
        return self._set("variant", value)

    @setter
    def icon(self, value: str) -> Self:
        return self._set("icon", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        bag = data["attrs"]
        bag.add_class("dcc-badge")
        variant = self.resolve("variant", ctx)
        if variant:
            bag.add_class(f"dcc-badge--{variant}")
        label = self.resolve("label", ctx)
        data["label"] = "" if label is None else label
        from ..icons import render_icon

        data["icon_html"] = render_icon(self.resolve("icon", ctx))
        return data
