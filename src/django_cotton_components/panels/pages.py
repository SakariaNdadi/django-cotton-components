from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from ..tables.views import TableMixin

if TYPE_CHECKING:
    from django.http import HttpRequest

    from .panel import Panel
    from .resource import Resource


class _ResourcePage(TemplateView):
    panel: Panel
    resource: type[Resource]
    action = "view"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.panel.check_access(request)
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
        ctx = super().get_context_data(**kwargs)
        ctx["panel"] = self.panel
        ctx["resource_label"] = self.resource.label()
        ctx["nav"] = self.panel.navigation(self.request)
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
        ctx["fields"] = [
            (f.verbose_name.title(), getattr(obj, f.name)) for f in self.resource.model._meta.fields
        ]
        ctx["edit_url"] = self._url("edit", pk=obj.pk)
        return ctx
