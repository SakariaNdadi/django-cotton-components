from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from django import template
from django.templatetags.static import static
from django.utils.safestring import SafeString, mark_safe

if TYPE_CHECKING:
    from django.forms import BaseForm

    from django_control_components.core.component import Component
    from django_control_components.schemas.schema import Schema

register = template.Library()

# Pinned exactly. A floating range let a production app inherit an upstream
# regression on its next page load. Bump deliberately, in lockstep with the
# vendored copies fetched by ``manage.py dcc_vendor_assets``.
ALPINE_VERSION = "3.17.1"
_ALPINE_SRC = f"https://cdn.jsdelivr.net/npm/alpinejs@{ALPINE_VERSION}/dist/cdn.min.js"
_ALPINE_FOCUS_SRC = f"https://cdn.jsdelivr.net/npm/@alpinejs/focus@{ALPINE_VERSION}/dist/cdn.min.js"
# Vendored file names under ``DCC["VENDOR_ASSET_DIR"]`` (CDN URL -> local basename).
# ``manage.py dcc_vendor_assets`` writes exactly these names.
VENDOR_NAMES = {
    "htmx": "htmx.min.js",
    _ALPINE_SRC: "alpine.min.js",
    _ALPINE_FOCUS_SRC: "alpine-focus.min.js",
}


def _script(
    url: str, *, vendor: bool, vendor_dir: str, sri: dict[str, str], vendor_key: str | None = None
) -> str:
    """One ``<script defer>`` tag — self-hosted when ``vendor``, else CDN with an
    optional ``integrity`` from ``DCC["ASSET_SRI"]``."""
    key = vendor_key or url
    if vendor and key in VENDOR_NAMES:
        return f'<script defer src="{static(vendor_dir + VENDOR_NAMES[key])}"></script>'
    integrity = sri.get(url)
    attrs = f' integrity="{integrity}" crossorigin="anonymous"' if integrity else ""
    return f'<script defer src="{url}"{attrs}></script>'


@register.simple_tag
def dcc_assets(
    *, alpine: bool = True, htmx: bool = True, icons: bool = True, focus: bool = True
) -> SafeString:
    """Emit the component stylesheet plus the htmx, Alpine.js and icon assets.

    Pass ``alpine=False`` / ``htmx=False`` / ``icons=False`` if the host page
    already loads them. Tables, actions and wizards drive their mutations through
    htmx, so it is on by default. ``focus=False`` skips the Alpine focus plugin
    that ``x-trap`` (modal / drawer focus containment) depends on.

    Set ``DCC["VENDOR_ASSETS"] = True`` to serve htmx / Alpine / focus from the
    project's own static files; ``DCC["ASSET_SRI"]`` adds integrity hashes to any
    CDN asset that stays remote.
    """
    from ..conf import dcc_settings
    from ..htmx import HTMX_SRC
    from ..icons import icon_assets

    vendor = bool(dcc_settings.VENDOR_ASSETS)
    vendor_dir = dcc_settings.VENDOR_ASSET_DIR
    sri = dcc_settings.ASSET_SRI or {}

    parts = [f'<link rel="stylesheet" href="{static("dcc/dcc.css")}">']
    if icons:
        icon_html = str(icon_assets())
        if icon_html:
            parts.append(icon_html)
    if htmx:
        parts.append(
            _script(HTMX_SRC, vendor=vendor, vendor_dir=vendor_dir, sri=sri, vendor_key="htmx")
        )
    # dcc.js MUST load before Alpine so it can register its `alpine:init`
    # listener before Alpine starts and scans the DOM.
    parts.append(f'<script defer src="{static("dcc/dcc.js")}"></script>')
    if alpine:
        # Plugins must load before Alpine core; `defer` preserves order.
        if focus:
            parts.append(_script(_ALPINE_FOCUS_SRC, vendor=vendor, vendor_dir=vendor_dir, sri=sri))
        parts.append(_script(_ALPINE_SRC, vendor=vendor, vendor_dir=vendor_dir, sri=sri))
    return mark_safe("\n".join(parts))  # noqa: S308  -- fixed strings + static() URL


@register.simple_tag
def dcc_studio_assets() -> SafeString:
    """The studio builder's CSS + JS. Emit inside a page that already ran
    ``{% dcc_assets %}`` (the builder needs htmx and Alpine)."""
    css = static("dcc/dcc-studio.css")
    js = static("dcc/dcc-studio.js")
    return mark_safe(  # noqa: S308  -- fixed strings + static() URLs
        f'<link rel="stylesheet" href="{css}">\n<script defer src="{js}"></script>'
    )


@register.simple_tag
def dcc_icon(name: str, css_class: str = "") -> SafeString:
    """Render a named icon through the active icon set."""
    from django_control_components.icons import render_icon

    return render_icon(name, css_class=css_class)


@register.simple_tag(takes_context=True)
def dcc_render(context: template.Context, component: Component) -> SafeString:
    """Render a Python component instance inside a template."""
    from django_control_components.core.context import RenderContext

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
