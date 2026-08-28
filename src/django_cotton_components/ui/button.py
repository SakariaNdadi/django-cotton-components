from __future__ import annotations

from typing import Any, Self

from ..core.attributes import AttributeBag
from ..core.component import Component, setter
from ..core.context import RenderContext
from ..icons import render_icon

_VARIANTS = {"primary", "secondary", "danger", "ghost", "link"}


class Button(Component):
    """The one button. Renders ``<a>`` when given ``href``, else ``<button>``.

    Callers attach behaviour (an htmx :class:`AttributeBag`, Alpine handlers) via
    :meth:`attributes`; those merge into the same attribute bag as the styling
    classes, so a template only ever prints ``{{ attrs }}``.
    """

    template_name = "django_cotton_components/ui/button.html"
    _base_class = "dcc-btn"

    @setter
    def label(self, value: str) -> Self:
        return self._set("label", value)

    @setter
    def icon(self, value: str) -> Self:
        return self._set("icon", value)

    @setter
    def variant(self, value: str) -> Self:
        return self._set("variant", value if value in _VARIANTS else "secondary")

    @setter
    def size(self, value: str) -> Self:
        return self._set("size", value)

    @setter
    def href(self, value: str) -> Self:
        return self._set("href", value)

    @setter
    def type(self, value: str) -> Self:
        return self._set("type", value)

    @setter
    def disabled(self, value: bool = True) -> Self:
        return self._set("disabled", value)

    @setter
    def attributes(self, value: AttributeBag | dict[str, Any]) -> Self:
        current = self._config.get("attributes")
        bag = current if isinstance(current, AttributeBag) else AttributeBag()
        bag.update(value.as_dict() if isinstance(value, AttributeBag) else dict(value))
        return self._set("attributes", bag)

    # -- rendering ---------------------------------------------------

    def _classes(self, ctx: RenderContext) -> list[str]:
        out = [self._base_class]
        out.append(f"{self._base_class}--{self._config.get('variant', 'secondary')}")
        size = self._config.get("size")
        if size:
            out.append(f"{self._base_class}--{size}")
        return out

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        bag: AttributeBag = data["attrs"]
        extra = self._config.get("attributes")
        if isinstance(extra, AttributeBag):
            bag.update(extra.as_dict())
        for cls in self._classes(ctx):
            bag.add_class(cls)
        label = self.resolve("label", ctx)
        data["label"] = "" if label is None or label is False else label
        data["icon_html"] = render_icon(self.resolve("icon", ctx))
        data["href"] = self.resolve("href", ctx) or ""
        data["type"] = self._config.get("type", "button")
        data["disabled"] = bool(self._config.get("disabled"))
        return data


class IconButton(Button):
    """A button whose visible content is only an icon; ``label`` is the a11y name."""

    _base_class = "dcc-btn"

    def _classes(self, ctx: RenderContext) -> list[str]:
        return [*super()._classes(ctx), "dcc-btn--icon"]

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        if data["label"]:
            data["attrs"].set("aria-label", data["label"])
        data["label"] = ""
        return data
