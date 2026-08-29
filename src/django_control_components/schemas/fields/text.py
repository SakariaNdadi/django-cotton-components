from __future__ import annotations

from typing import Any

from .base import Field


class TextInput(Field):
    template_name = "django_control_components/controls/input.html"
    input_type = "text"
    widget_css_class = "dcc-input"


class EmailInput(TextInput):
    input_type = "email"


class Hidden(Field):
    template_name = "django_control_components/controls/input.html"
    input_type = "hidden"
    uses_django_widget = False

    def get_view_data(self, ctx: Any) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["label_display"] = False
        return data


class Textarea(Field):
    template_name = "django_control_components/controls/textarea.html"
    widget_css_class = "dcc-textarea"


class PasswordInput(Field):
    template_name = "django_control_components/controls/password.html"
    uses_django_widget = False
    input_type = "password"
