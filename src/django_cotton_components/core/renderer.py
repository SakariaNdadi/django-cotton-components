from __future__ import annotations

from typing import TYPE_CHECKING

from django.template.loader import render_to_string
from django.utils.safestring import SafeString

if TYPE_CHECKING:
    from .component import Component
    from .context import RenderContext


def render_component(component: Component, ctx: RenderContext) -> SafeString:
    """Render a component's cotton template with fully-evaluated context.

    The Python path renders the leaf template directly via ``render_to_string``
    rather than round-tripping through a ``<c-...>`` tag string: the props are
    already a typed dict, and stringifying them into a tag is exactly where
    escaping bugs come from.
    """
    if not component.template_name:
        raise ValueError(f"{type(component).__name__} has no template_name")
    data = component.get_view_data(ctx)
    request = ctx.request
    html = render_to_string(component.template_name, data, request=request)
    return SafeString(html)
