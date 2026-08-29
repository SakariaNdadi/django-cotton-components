from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import Field

if TYPE_CHECKING:
    from ...core.context import RenderContext


class Checkbox(Field):
    template_name = "django_control_components/controls/checkbox.html"
    uses_django_widget = False

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["label_display"] = False
        data["checked"] = bool(data["value"])
        data["value"] = "on"
        return data


class Toggle(Checkbox):
    template_name = "django_control_components/controls/toggle.html"
