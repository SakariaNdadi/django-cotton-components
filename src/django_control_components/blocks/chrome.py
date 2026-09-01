"""Chrome blocks - the page frame a studio-built app sits in.

``AppShell`` is the root: a header, a sidebar, the content, a footer. It reuses
the existing ``.dcc-panel`` structure and the ``dccShell()`` Alpine component
(nav drawer + persisted 3-state theme) so a shell built here renders the same
markup as the hand-coded ``panels/base.html``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from ..core.component import setter
from .base import Block

if TYPE_CHECKING:
    from ..core.context import RenderContext


class AppShell(Block):
    """Root page frame: ``topbar`` / ``sidebar`` / ``content`` / ``footer``."""

    slots = ("topbar", "sidebar", "content", "footer")
    template_name = "django_control_components/blocks/app_shell.html"

    @setter
    def sidebar_width(self, value: str) -> Self:
        return self._set("sidebar_width", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["sidebar_width"] = self._config.get("sidebar_width", "15rem")
        data["has_sidebar"] = bool(self._slots.get("sidebar"))
        data["has_topbar"] = bool(self._slots.get("topbar"))
        data["has_footer"] = bool(self._slots.get("footer"))
        return data


class Navbar(Block):
    """A horizontal bar with a leading and a trailing region."""

    slots = ("start", "end")
    template_name = "django_control_components/blocks/navbar.html"

    @setter
    def brand(self, value: str) -> Self:
        return self._set("brand", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["brand"] = self._config.get("brand", "")
        return data


class Sidebar(Block):
    """A vertical nav column. Holds nav-link blocks (or anything) in ``default``;
    a full nav-tree data source arrives with the ``Page`` model."""

    slots = ("default",)
    template_name = "django_control_components/blocks/sidebar.html"

    @setter
    def brand(self, value: str) -> Self:
        return self._set("brand", value)

    @setter
    def brand_icon(self, value: str) -> Self:
        return self._set("brand_icon", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["brand"] = self._config.get("brand", "")
        data["brand_icon"] = self._config.get("brand_icon", "")
        return data


class Footer(Block):
    """A page footer."""

    slots = ("default",)
    template_name = "django_control_components/blocks/footer.html"
