from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from .. import htmx
from ..tables.views import TableMixin
from .guards import LoginRequired

if TYPE_CHECKING:
    from django.http import HttpRequest

    from .panel import Panel
    from .resource import Resource


def _guarded(panel: Panel, request: HttpRequest) -> HttpResponseBase | None:
    """Run the panel guards; return a login redirect if a guard raised
    ``LoginRequired``, else ``None`` (``PermissionDenied`` propagates)."""
    try:
        panel.check_access(request)
    except LoginRequired:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.get_full_path(), panel.get_login_url())
    return None


class PanelPage(TemplateView):
    """A page mounted on a panel that is not tied to a resource (dashboards,
    custom pages). Subclass, set ``slug`` / ``nav_label`` / ``nav_icon``, and
    override ``get_context_data`` or the page's own hooks."""

    panel: Panel
    slug: str = ""
    nav_label: str = ""
    nav_icon: str = ""
    nav_group: str = ""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        redirect_response = _guarded(self.panel, request)
        if redirect_response is not None:
            return redirect_response
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        from .nav import build_nav

        ctx = super().get_context_data(**kwargs)
        ctx["panel"] = self.panel
        ctx["nav"] = self.panel.navigation(self.request)
        ctx["nav_tree"] = build_nav(self.panel, self.request)
        ctx["resource_label"] = self.nav_label or self.slug.title() or "Dashboard"
        return ctx


#: Deprecated pre-1.0 alias. Use :class:`PanelPage`.
_PanelPage = PanelPage


class DashboardPage(PanelPage):
    """A grid of :class:`~.widgets.Widget`. Override :meth:`widgets`."""

    template_name = "django_cotton_components/panels/dashboard.html"
    page_title = "Dashboard"
    nav_label = "Dashboard"
    nav_icon = "gauge-high"

    def widgets(self, request: HttpRequest) -> list[Any]:
        return []

    def _widget_instances(self, request: HttpRequest) -> list[Any]:
        if not hasattr(self, "_widget_cache"):
            widgets = self.widgets(request)
            for index, widget in enumerate(widgets):
                if not widget._config.get("id"):
                    widget._auto_id = f"w{index}"
            self._widget_cache = widgets
        return self._widget_cache

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        widget_id = request.GET.get("_dcc_widget")
        if htmx.is_htmx(request) and widget_id:
            for widget in self._widget_instances(request):
                if widget.get_id() == widget_id:
                    return HttpResponse(widget.render_content(request))
            raise Http404("No such widget")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = self.page_title
        widgets = self._widget_instances(self.request)
        ctx["widgets"] = [w.render(self.request) for w in widgets]
        assets: dict[str, Any] = {}
        for widget in widgets:
            for asset in widget.get_assets():
                assets[asset.url] = asset
        ctx["widget_assets"] = list(assets.values())
        return ctx


class _ResourcePage(TemplateView):
    panel: Panel
    resource: type[Resource]
    action = "view"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        redirect_response = _guarded(self.panel, request)
        if redirect_response is not None:
            return redirect_response
        if not self.resource.can(request, self.action, self._object(request, kwargs)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def _object(self, request: HttpRequest, kwargs: dict[str, Any]) -> Any:
        if "pk" in kwargs:
            return get_object_or_404(self.resource.get_queryset(request), pk=kwargs["pk"])
        return None

    def _url(self, name: str, **kwargs: Any) -> str:
        return reverse(f"{self.panel.namespace}:{self.resource.slug()}-{name}", kwargs=kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        from .nav import build_nav

        ctx = super().get_context_data(**kwargs)
        ctx["panel"] = self.panel
        ctx["resource_label"] = self.resource.label()
        ctx["nav"] = self.panel.navigation(self.request)
        ctx["nav_tree"] = build_nav(self.panel, self.request)
        return ctx


class ListRecords(TableMixin, _ResourcePage):
    template_name = "django_cotton_components/panels/list.html"
    action = "view"

    def get_table(self) -> Any:
        return self.resource.build_table(request=self.request)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["can_create"] = self.resource.can(self.request, "add")
        ctx["create_url"] = self._url("create")
        return ctx


class _FormPage(_ResourcePage):
    template_name = "django_cotton_components/panels/form.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self._render(request, self._form(request))

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self._object(request, kwargs)
        form = self._form(request, data=request.POST, files=request.FILES, instance=obj)
        if form.is_valid():
            saved = form.save()
            schema = self.resource.build_schema(request=request)
            if schema.image_specs():
                schema.process_images(saved)
            return redirect(self._url("edit", pk=saved.pk))
        return self._render(request, form)

    def _form(self, request: HttpRequest, **kw: Any) -> Any:
        schema = self.resource.build_schema(request=request)
        instance = kw.pop("instance", self._object(request, self.kwargs))
        return schema.build_form(instance=instance, **kw)

    def _render(self, request: HttpRequest, form: Any) -> HttpResponse:
        schema = self.resource.build_schema(request=request)
        ctx = self.get_context_data()
        ctx["schema_html"] = schema.render(request=request, form=form)
        ctx["form"] = form
        return self.render_to_response(ctx)


class CreateRecord(_FormPage):
    action = "add"


class EditRecord(_FormPage):
    action = "change"


class ViewRecord(_ResourcePage):
    template_name = "django_cotton_components/panels/view.html"
    action = "view"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        obj = self._object(self.request, self.kwargs)
        ctx["object"] = obj
        ctx["infolist_html"] = self.resource.build_infolist(request=self.request).render(
            request=self.request, record=obj
        )
        ctx["edit_url"] = self._url("edit", pk=obj.pk)
        ctx["delete_url"] = self._url("delete", pk=obj.pk)
        ctx["can_delete"] = self.resource.can(self.request, "delete", obj)
        return ctx


class DeleteRecord(_ResourcePage):
    template_name = "django_cotton_components/panels/delete.html"
    action = "delete"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self._object(self.request, self.kwargs)
        ctx["cancel_url"] = self._url("view", pk=self.kwargs["pk"])
        return ctx

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self._object(request, kwargs)
        obj.delete()
        return redirect(self._url("list"))
