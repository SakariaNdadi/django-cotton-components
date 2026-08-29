from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from ...core.component import UNSET, setter
from .base import Field

if TYPE_CHECKING:
    from ...core.context import RenderContext


class _ChoiceField(Field):
    uses_django_widget = False
    multiple = False

    @setter
    def options(self, value: Any) -> Self:
        return self._set("options", value)

    @setter
    def searchable(self, value: bool = True) -> Self:
        return self._set("searchable", value)

    def _options(self, ctx: RenderContext) -> list[tuple[str, str]]:
        configured = self.resolve("options", ctx)
        if configured is not UNSET and configured is not None:
            pairs = configured.items() if isinstance(configured, dict) else configured
            return [(str(v), str(label)) for v, label in pairs]

        bound = self._bound(ctx)
        if bound is not None and hasattr(bound.field, "choices"):
            out = []
            for value, label in bound.field.choices:
                if value == "" or value is None:
                    continue
                out.append((str(value), str(label)))
            return out
        return []

    def _selected(self, ctx: RenderContext) -> list[str]:
        bound = self._bound(ctx)
        raw = bound.value() if bound is not None else self.resolve("default", ctx)
        if raw in (None, UNSET, ""):
            return []
        if isinstance(raw, (list, tuple, set)):
            return [str(x) for x in raw]
        return [str(raw)]

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        options = self._options(ctx)
        data["options"] = options
        data["selected_values"] = self._selected(ctx)
        data["multiple"] = self.multiple
        searchable = self.resolve("searchable", ctx)
        data["searchable"] = bool(searchable) if searchable is not UNSET else False
        data["widget_html"] = ""
        return data


class Select(_ChoiceField):
    template_name = "django_control_components/controls/select.html"


class MultiSelect(_ChoiceField):
    template_name = "django_control_components/controls/select.html"
    multiple = True

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        if data["searchable"] is False and "searchable" not in self._config:
            data["searchable"] = True
        return data


class Radio(_ChoiceField):
    template_name = "django_control_components/controls/radio.html"

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["choices"] = data["options"]
        selected = data["selected_values"]
        data["value"] = selected[0] if selected else ""
        return data
