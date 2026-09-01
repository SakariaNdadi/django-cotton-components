from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from django.utils.text import capfirst

from ...conf import dcc_settings
from ...core.attributes import AttributeBag
from ...core.component import UNSET, Component, setter
from ...core.concerns import HasColumnSpan, HasHint, HasLabel, HasState, HasVisibilityRules

if TYPE_CHECKING:
    from django.forms import BoundField

    from ...core.context import RenderContext


class Field(HasLabel, HasHint, HasState, HasColumnSpan, HasVisibilityRules, Component):
    """Base for every form field component.

    A field never validates. It reads presentation defaults from the bound
    Django field only where the caller left a value ``UNSET``, and always
    renders a real, correctly-named HTML control.
    """

    #: whether this control delegates markup to Django's widget (plain fields)
    uses_django_widget: bool = True
    #: CSS class applied to the Django widget when ``uses_django_widget``
    widget_css_class: str = "dcc-input"
    input_type: str = "text"

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        if name is None:
            raise ValueError(f"{type(self).__name__} requires a field name")
        super().__init__(name, **kwargs)

    # -- extra setters -------------------------------------------------

    @setter
    def live(self, debounce: int | bool = True) -> Self:
        ms = dcc_settings.LIVE_VALIDATION_DEBOUNCE_MS if debounce is True else int(debounce)
        return self._set("live_debounce", ms)

    # -- binding helpers --------------------------------------------

    def _bound(self, ctx: RenderContext) -> BoundField | None:
        form = ctx.form
        if form is None or self._name not in form.fields:
            return None
        return form[self._name]

    def _pick(self, key: str, ctx: RenderContext, fallback: Any) -> Any:
        configured = self.resolve(key, ctx)
        return fallback if configured is UNSET else configured

    # -- view data -------------------------------------------------

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        bound = self._bound(ctx)
        djfield = bound.field if bound is not None else None

        name = bound.html_name if bound is not None else self._name
        field_id = bound.auto_id if bound is not None else f"id_{self._name}"

        default_label: Any = capfirst((self._name or "").replace("_", " "))
        if djfield and djfield.label:
            default_label = djfield.label
        label = self._pick("label", ctx, default_label)
        required = self._pick("required", ctx, djfield.required if djfield else False)
        disabled = self._pick("disabled", ctx, djfield.disabled if djfield else False)
        readonly = bool(self.resolve("readonly", ctx) or False)
        help_text = self._pick("help_text", ctx, djfield.help_text if djfield else "")
        placeholder = self.resolve("placeholder", ctx)
        errors = list(bound.errors) if bound is not None else []
        value = bound.value() if bound is not None else self.resolve("default", ctx)
        if value is UNSET:
            value = None

        extra = AttributeBag(self._config.get("extra_attributes"))
        live_url = None
        if "live_debounce" in self._config and ctx.form is not None:
            live_url = ctx.extra.get("live_url")

        data: dict[str, Any] = {
            "component": self,
            "id": field_id,
            "name": name,
            "type": self.input_type,
            "label": label,
            "label_display": self._config.get("label_display", True),
            "required": bool(required),
            "disabled": bool(disabled),
            "readonly": readonly,
            "help_text": help_text or "",
            "placeholder": placeholder if placeholder is not UNSET else "",
            "errors": errors,
            "value": value,
            "attrs": extra,
            "visible_expr": self._visible_expr(),
            "column_span": self._config.get("column_span"),
            "live_url": live_url,
            "htmx_attrs": "",
        }

        if self.uses_django_widget and bound is not None:
            widget_attrs: dict[str, str | bool] = {"class": self.widget_css_class}
            if data["placeholder"]:
                widget_attrs["placeholder"] = data["placeholder"]
            data["widget_html"] = bound.as_widget(attrs=widget_attrs)
        else:
            data["widget_html"] = ""

        return data
