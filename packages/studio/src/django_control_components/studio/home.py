"""Resolve where a signed-in user should land inside a panel.

Cascade: an explicit ``UserPreference`` → a dashboard that is a default for one
of the user's groups → a panel-wide default dashboard → the first dashboard the
user may see → the first nav item → the panel index.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.urls import NoReverseMatch, reverse

if TYPE_CHECKING:
    from django.http import HttpRequest

    from ..panels.panel import Panel


def resolve_home(request: HttpRequest, panel: Panel) -> str:
    user = getattr(request, "user", None)
    ns = panel.namespace

    preferred = _from_preference(user, panel)
    if preferred:
        return preferred

    home_page = _home_page(user, panel)
    if home_page:
        return home_page

    dashboard = _default_dashboard(user)
    if dashboard is not None:
        try:
            return reverse(f"{ns}:studio-dashboard", kwargs={"dash_slug": dashboard.slug})
        except NoReverseMatch:
            pass

    from ..panels.nav import build_nav

    for node in build_nav(panel, request):
        target = node if node.url else next((c for c in node.children if c.url), None)
        if target is not None and target.url:
            return target.url

    try:
        return reverse(f"{ns}:index")
    except NoReverseMatch:
        return "/"


def _from_preference(user: Any, panel: Panel) -> str:
    if user is None or not user.is_authenticated:
        return ""
    pref = getattr(user, "dcc_preference", None)
    if pref is None or not pref.home_kind:
        return ""
    ns = panel.namespace
    try:
        if pref.home_kind == "dashboard":
            return reverse(f"{ns}:studio-dashboard", kwargs={"dash_slug": pref.home_target})
        if pref.home_kind == "spec":
            return reverse(f"{ns}:studio-list", kwargs={"spec_slug": pref.home_target})
        if pref.home_kind == "url":
            return str(pref.home_target)
    except NoReverseMatch:
        return ""
    return ""


def _home_page(user: Any, panel: Panel) -> str:
    """A ``Page`` for this panel flagged ``is_home`` and visible to the user."""
    from .models import Page

    page = Page.objects.filter(
        mount="panel", panel=panel.name, is_home=True, is_enabled=True
    ).first()
    if page is None or not page.is_visible_to(user):
        return ""
    try:
        return reverse(f"{panel.namespace}:page", kwargs={"route": page.route})
    except NoReverseMatch:
        return ""


def _default_dashboard(user: Any) -> Any:
    from .models import PanelDashboard

    if user is not None and user.is_authenticated:
        group_default = (
            PanelDashboard.objects.filter(is_enabled=True, default_for_groups__in=user.groups.all())
            .order_by("pk")
            .first()
        )
        if group_default is not None and group_default.is_visible_to(user):
            return group_default

    panel_default = (
        PanelDashboard.objects.filter(is_enabled=True, is_default=True).order_by("pk").first()
    )
    if panel_default is not None and panel_default.is_visible_to(user):
        return panel_default

    for dashboard in PanelDashboard.objects.filter(is_enabled=True).order_by("pk"):
        if dashboard.is_visible_to(user):
            return dashboard
    return None
