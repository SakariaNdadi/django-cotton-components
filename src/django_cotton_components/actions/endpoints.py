from __future__ import annotations

from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.views import View

from .. import htmx
from .registry import registry


class ActionView(View):
    """Single endpoint for every registered action.

    GET  -> render the confirmation / schema modal.
    POST -> authorize (again), re-scope targets to the owner's queryset, execute.
    """

    def _resolve(self, owner_key: str, action_name: str) -> tuple[Any, Any]:
        found = registry.resolve(owner_key, action_name)
        if found is None:
            raise Http404("Unknown action")
        return found

    def _targets(self, request: HttpRequest, owner: Any, action: Any) -> list[Any]:
        scope = owner.get_action_queryset(request)
        if action.is_bulk:
            ids = request.POST.getlist("records") or request.GET.getlist("records")
            if not ids:
                return []
            # re-scope: intersect requested ids with what the owner exposes
            return list(scope.filter(pk__in=ids))
        raw = request.POST.get("record") or request.GET.get("record")
        if raw is None:
            return []
        obj = scope.filter(pk=raw).first()
        return [obj] if obj is not None else []

    def get(self, request: HttpRequest, owner_key: str, action_name: str) -> HttpResponse:
        owner, action = self._resolve(owner_key, action_name)
        records = self._targets(request, owner, action)
        if not action.is_authorized(request, records[0] if records else None):
            return HttpResponse(status=403)

        form_html: Any = ""
        schema = action._config.get("schema")
        if schema is not None:
            form_html = schema.render(request=request, form=schema.build_form())
        return HttpResponse(
            action.render_modal(request=request, records=records, form_html=form_html)
        )

    def post(self, request: HttpRequest, owner_key: str, action_name: str) -> HttpResponse:
        owner, action = self._resolve(owner_key, action_name)
        records = self._targets(request, owner, action)
        if not action.is_authorized(request, records[0] if records else None):
            return HttpResponse(status=403)

        data: dict[str, Any] = {}
        schema = action._config.get("schema")
        if schema is not None:
            form = schema.build_form(data=request.POST)
            if not form.is_valid():
                return HttpResponse(
                    action.render_modal(
                        request=request,
                        records=records,
                        form_html=schema.render(request=request, form=form),
                    )
                )
            data = form.cleaned_data

        action.run(request, records, data)

        resp = HttpResponse(status=204)
        return htmx.response.trigger(
            resp,
            {"dcc:toast": action.success_message(), "dcc:refresh": True},
        )
