from __future__ import annotations

from typing import Any, Self

from ..core.attributes import AttributeBag
from ..core.component import Component, setter
from ..core.context import RenderContext


class Checkbox(Component):
    """A bare labelled checkbox — no field chrome.

    Used for table row-selection and anywhere a plain toggle is needed. Schema
    form fields keep their own error/help wrapper.
    """

    template_name = "django_control_components/ui/checkbox.html"

    @setter
    def label(self, value: str) -> Self:
        return self._set("label", value)

    @setter
    def value(self, value: str) -> Self:
        return self._set("value", value)

    @setter
    def checked(self, value: bool = True) -> Self:
        return self._set("checked", value)

    @setter
    def attributes(self, value: AttributeBag | dict[str, Any]) -> Self:
        current = self._config.get("attributes")
        bag = current if isinstance(current, AttributeBag) else AttributeBag()
        bag.update(value.as_dict() if isinstance(value, AttributeBag) else dict(value))
        return self._set("attributes", bag)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        bag: AttributeBag = data["attrs"]
        extra = self._config.get("attributes")
        if isinstance(extra, AttributeBag):
            bag.update(extra.as_dict())
        data["input_name"] = self._name or ""
        data["value"] = self.resolve("value", ctx) or ""
        data["checked"] = bool(self._config.get("checked"))
        label = self.resolve("label", ctx)
        data["label"] = "" if label is None else label
        return data
