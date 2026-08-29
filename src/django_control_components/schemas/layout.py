from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Self

from django.utils.safestring import SafeString, mark_safe

from ..core.component import Component, setter
from ..core.concerns import HasChildComponents

if TYPE_CHECKING:
    from ..core.context import RenderContext


class Layout(HasChildComponents, Component):
    """A container that renders child components into a slot."""

    def __init__(self, title: str | None = None, **kwargs: Any) -> None:
        super().__init__(title, **kwargs)
        self._children: list[Component] = []

    @property
    def title(self) -> str | None:
        return self._name

    def _render_children(self, ctx: RenderContext) -> SafeString:
        # Every part is already a SafeString from Component.render / render_to_string.
        parts = [str(child.render(ctx.child(parent=self))) for child in self._children]
        return mark_safe("".join(parts))  # noqa: S308

    def _visible_expr(self) -> str:
        return ""

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        return {
            "component": self,
            "title": self._name,
            "children_html": self._render_children(ctx),
            "visible_expr": self._visible_expr(),
        }

    def iter_fields(self) -> Iterator[Component]:
        for child in self._children:
            if isinstance(child, Layout):
                yield from child.iter_fields()
            else:
                yield child


class Section(Layout):
    template_name = "django_control_components/layout/section.html"

    @setter
    def columns(self, value: int) -> Self:
        return self._set("columns", value)

    @setter
    def description(self, value: str) -> Self:
        return self._set("description", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["columns"] = self._config.get("columns", 1)
        data["description"] = self._config.get("description", "")
        return data


class Grid(Layout):
    template_name = "django_control_components/layout/grid.html"

    @setter
    def columns(self, value: int) -> Self:
        return self._set("columns", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["columns"] = self._config.get("columns", 2)
        return data


class Fieldset(Layout):
    template_name = "django_control_components/layout/fieldset.html"

    @setter
    def columns(self, value: int) -> Self:
        return self._set("columns", value)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["columns"] = self._config.get("columns", 1)
        return data


class Tab(Layout):
    template_name = "django_control_components/layout/grid.html"


class Tabs(Layout):
    template_name = "django_control_components/layout/tabs.html"

    def schema(self, components: list[Component]) -> Self:
        for c in components:
            if not isinstance(c, Tab):
                raise TypeError("Tabs.schema() accepts only Tab instances")
        self._children = list(components)
        return self

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        tabs = []
        for i, child in enumerate(self._children):
            assert isinstance(child, Tab)  # enforced in schema()
            child_ctx = ctx.child(parent=self)
            tabs.append(
                {"title": child.title or f"Tab {i + 1}", "html": child._render_children(child_ctx)}
            )
        return {"component": self, "tabs": tabs, "visible_expr": ""}
