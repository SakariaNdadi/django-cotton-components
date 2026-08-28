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
def dcc_assets(*, alpine: bool = True, htmx: bool = True, icons: bool = True) -> SafeString:
    """Emit the component stylesheet plus the htmx, Alpine.js and icon assets.

    Pass ``alpine=False`` / ``htmx=False`` / ``icons=False`` if the host page
    already loads them. Tables, actions and wizards drive their mutations through
    htmx, so it is on by default.
    """
    from ..htmx import HTMX_SRC
    from ..icons import icon_assets

    parts = [f'<link rel="stylesheet" href="{static("dcc/dcc.css")}">']
    if icons:
        icon_html = str(icon_assets())
        if icon_html:
            parts.append(icon_html)
    if htmx:
        parts.append(f'<script src="{HTMX_SRC}" defer></script>')
    # dcc.js MUST load before Alpine so it can register its `alpine:init`
    # listener before Alpine starts and scans the DOM.
    parts.append(f'<script defer src="{static("dcc/dcc.js")}"></script>')
    if alpine:
        parts.append(f'<script defer src="{_ALPINE_SRC}"></script>')
    return mark_safe("\n".join(parts))  # noqa: S308  -- fixed strings + static() URL


@register.simple_tag
def dcc_icon(name: str, css_class: str = "") -> SafeString:
    """Render a named icon through the active icon set."""
    from django_cotton_components.icons import render_icon

    return render_icon(name, css_class=css_class)


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
