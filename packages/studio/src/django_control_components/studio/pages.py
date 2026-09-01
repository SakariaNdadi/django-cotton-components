from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import Http404, HttpResponseBase

from ..panels import pages as panel_pages
from ..panels.pages import _ResourcePage
from .deserialize import build_widgets_from_spec
from .models import DashboardSpec, PanelDashboard
from .resource import DynamicResource

if TYPE_CHECKING:
    from ..panels.resource import Resource


class _ResolveSpec(_ResourcePage):
    """Turn ``<spec_slug>`` into ``self.resource`` before the panel page runs."""

    resource: type[Resource]

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponseBase:
        slug = kwargs.get("spec_slug")
        try:
            spec = DashboardSpec.objects.get(slug=slug, is_enabled=True)
        except DashboardSpec.DoesNotExist:
            raise Http404("No such dashboard") from None
        self.resource = DynamicResource.for_spec(spec)
        return super().dispatch(request, *args, **kwargs)

    def _url(self, name: str, **kwargs: Any) -> str:
        from django.urls import reverse

        kwargs.setdefault("spec_slug", self.resource.slug())
        return reverse(f"{self.panel.namespace}:studio-{name}", kwargs=kwargs)


class DynamicList(_ResolveSpec, panel_pages.ListRecords):
    pass


class DynamicCreate(_ResolveSpec, panel_pages.CreateRecord):
    pass


class DynamicView(_ResolveSpec, panel_pages.ViewRecord):
    pass


class DynamicEdit(_ResolveSpec, panel_pages.EditRecord):
    pass


class DynamicDelete(_ResolveSpec, panel_pages.DeleteRecord):
    pass


class DynamicPage(panel_pages.PanelPage):
    """Serve a stored :class:`~.models.Page` (``mount="panel"``) as an in-app
    page: the panel guards run first, then the block tree renders in the panel
    shell. A page the user may not see 404s, not 403s."""

    template_name = "django_control_components/studio/panel_page.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        from django.utils.safestring import mark_safe

        from .routing import render_page_tree, resolve_page

        page = resolve_page("panel", self.panel.name, kwargs.get("route", ""), self.request)
        ctx = super().get_context_data(**kwargs)
        ctx["page"] = page
        ctx["page_title"] = page.title
        ctx["resource_label"] = page.title
        ctx["content"] = mark_safe(render_page_tree(page, self.request))  # noqa: S308
        return ctx


class DynamicDashboardPage(panel_pages.DashboardPage):
    """Serve a stored :class:`PanelDashboard` row as a widget dashboard."""

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponseBase:
        try:
            self._spec = PanelDashboard.objects.get(slug=kwargs.get("dash_slug"), is_enabled=True)
        except PanelDashboard.DoesNotExist:
            raise Http404("No such dashboard") from None
        self.page_title = self._spec.label or self._spec.slug.title()
        return super().dispatch(request, *args, **kwargs)

    def widgets(self, request: Any) -> list[Any]:
        return build_widgets_from_spec(self._spec.widgets, request=request)
