"""Request-time resolution of :class:`~.models.Page` rows behind a catch-all.

URL patterns are built once at import; page rows change at runtime. So a page is
resolved at request time behind a catch-all the dev opts into per mount point,
never by rebuilding the URLconf on save::

    urlpatterns = [
        path("studio/", include("django_control_components.studio.urls")),
        path("panel/", admin_panel.mount()),
        path("", include(dcc_pages("site"))),   # public pages — mount LAST
    ]

Inside a panel the equivalent catch-all is appended automatically (last, under a
reserved ``p/`` prefix) whenever the panel enables the studio.
"""

from __future__ import annotations

from typing import Any

from django.http import Http404
from django.shortcuts import render
from django.urls import re_path
from django.utils.safestring import mark_safe
from django.views import View

from ..core.context import RenderContext
from .models import Page


def resolve_page(mount: str, panel: str, route: str, request: Any) -> Page:
    """The enabled :class:`Page` at ``route`` for this mount, or ``Http404``.

    A page the visitor may not see raises **404, not 403** — a restricted page's
    existence must not leak from the status code.
    """
    try:
        page = Page.objects.get(mount=mount, panel=panel, route=route.strip("/"), is_enabled=True)
    except Page.DoesNotExist:
        raise Http404("No such page") from None
    if not page.is_visible_to(getattr(request, "user", None)):
        raise Http404("No such page")
    return page


def render_page_tree(page: Page, request: Any) -> str:
    block = page.build_tree(request)
    if block is None:
        return ""
    return str(block.render(RenderContext(request=request)))


class SitePageView(View):
    """Renders a ``mount="site"`` page in the public site shell."""

    def get(self, request: Any, route: str = "", **kwargs: Any) -> Any:
        page = resolve_page("site", "", route, request)
        return render(
            request,
            "django_control_components/studio/site_page.html",
            {
                "page": page,
                "page_title": page.seo_title or page.title,
                "seo_description": page.seo_description,
                "content": mark_safe(render_page_tree(page, request)),  # noqa: S308
            },
        )


def dcc_pages(mount: str = "site") -> list[Any]:
    """The catch-all URL patterns for ``Page`` rows with this ``mount``. Only
    the public ``"site"`` mount is dev-includable; the panel mount is wired by
    :class:`~django_control_components.panels.Panel` itself."""
    if mount != "site":
        raise ValueError("dcc_pages() mounts only the public 'site'; panels wire their own")
    return [re_path(r"^(?P<route>[\w./-]*)$", SitePageView.as_view(), name="dcc-page")]
