from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from django import template
from django.templatetags.static import static
from django.utils.safestring import SafeString, mark_safe

if TYPE_CHECKING:
    from django.forms import BaseForm

    from django_cotton_components.core.component import Component
    from django_cotton_components.schemas.schema import Schema

register = template.Library()

_ALPINE_SRC = "https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"


@register.simple_tag
def dcc_assets(*, alpine: bool = True) -> SafeString:
    """Emit the component stylesheet and (optionally) the Alpine.js script tag.

    Pass ``alpine=False`` if the host page already loads Alpine.
    """
    parts = [f'<link rel="stylesheet" href="{static("dcc/dcc.css")}">']
    # dcc.js MUST load before Alpine so it can register its `alpine:init`
    # listener before Alpine starts and scans the DOM.
    parts.append(f'<script defer src="{static("dcc/dcc.js")}"></script>')
    if alpine:
        parts.append(f'<script defer src="{_ALPINE_SRC}"></script>')
    return mark_safe("\n".join(parts))  # noqa: S308  -- fixed strings + static() URL


@register.simple_tag(takes_context=True)
def dcc_render(context: template.Context, component: Component) -> SafeString:
    """Render a Python component instance inside a template."""
    from django_cotton_components.core.context import RenderContext

    request = context.get("request")
    ctx = RenderContext(request=request, form=context.get("form"))
    return component.render(ctx)


@register.simple_tag(takes_context=True)
def dcc_form(context: template.Context, schema: Schema, form: BaseForm | None = None) -> SafeString:
    """Render a bound schema as a complete ``<form>`` including CSRF token."""
    request = context.get("request")
    return schema.render_form(request=request, form=form or context.get("form"))


@register.simple_tag
def get_field_errors(form: BaseForm, field_name: str) -> Any:
    warnings.warn(
        "{% get_field_errors %} is deprecated; the schema forms bridge renders "
        "field errors directly. This tag is removed in the next minor release.",
        DeprecationWarning,
        stacklevel=2,
    )
    if field_name in form.errors:
        return form.errors[field_name]
    return None
