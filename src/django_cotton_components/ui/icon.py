from __future__ import annotations

from typing import Any, Self

from ..core.component import Component, setter
from ..core.context import RenderContext
from ..icons import render_icon


class Icon(Component):
    """A single icon, rendered through the active icon set.

    The icon name is the positional argument: ``Icon.make("solid:pen")``.
    """

    template_name = "django_cotton_components/ui/icon.html"

    @setter
    def css_class(self, value: str) -> Self:
        return self._set("css_class", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["icon_html"] = render_icon(self._name, css_class=self._config.get("css_class", ""))
        return data
