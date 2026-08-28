from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import Http404, HttpResponseBase

from ..panels import pages as panel_pages
from ..panels.pages import _ResourcePage
from .models import DashboardSpec
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
