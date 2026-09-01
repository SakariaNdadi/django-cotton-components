from __future__ import annotations

from typing import Any, Self

from django.utils.safestring import SafeString

from ..core.component import Component, setter
from ..core.context import RenderContext


class Modal(Component):
    """One modal implementation: teleported overlay + focus trap.

    The body is supplied as pre-rendered HTML (``body``) because the Python
    render path has no slot mechanism. ``open_on_load`` starts it visible - the
    action endpoint swaps a ready-open modal into a mount point.
    """

    template_name = "django_control_components/ui/modal.html"

    @setter
    def heading(self, value: str) -> Self:
        return self._set("heading", value)

    @setter
    def size(self, value: str) -> Self:
        return self._set("size", value)

    @setter
    def body(self, value: SafeString | str) -> Self:
        return self._set("body", value)

    @setter
    def open_on_load(self, value: bool = True) -> Self:
        return self._set("open_on_load", value)

    @setter
    def dom_id(self, value: str) -> Self:
        return self._set("dom_id", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["heading"] = self.resolve("heading", ctx) or ""
        data["size"] = self._config.get("size", "")
        data["body_html"] = self._config.get("body", "")
        data["open_on_load"] = bool(self._config.get("open_on_load", True))
        data["dom_id"] = self._config.get("dom_id", "")
        return data
