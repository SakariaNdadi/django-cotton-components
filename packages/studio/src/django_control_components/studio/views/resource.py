"""The resource builder: edit a ``DashboardSpec``'s list table (columns +
filters) with the shared canvas. Schema and infolist keep their scaffolded
JSON — the form / detail builders come later."""

from __future__ import annotations

import json
from typing import Any

from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from ..deserialize import build_table_from_spec, validate_spec
from ..introspect import installed_models, resolve_model
from ..models import DashboardSpec, SpecRevision
from ..palette import palette
from ..scaffold import scaffold_spec
from .base import StudioView


class ResourceIndex(StudioView):
    template_name = "django_control_components/studio/resource_index.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(
            request,
            self.template_name,
            self.shell_context(
                specs=list(DashboardSpec.objects.order_by("slug")),
                models=installed_models(request),
            ),
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        label = (request.POST.get("model") or "").strip()
        try:
            model = resolve_model(label)
        except LookupError:
            raise Http404("no such model") from None
        if not any(row["label"] == label for row in installed_models(request)):
            raise Http404("model not available")

        spec = scaffold_spec(model, request=request)
        slug = model._meta.model_name or label.replace(".", "-")
        obj = DashboardSpec.objects.create(
            slug=slug,
            label=str(model._meta.verbose_name_plural).title(),
            model=label,
            **spec,
        )
        return redirect(f"{self.panel.namespace}:studio-resource", slug=obj.slug)


class ResourceBuilder(StudioView):
    template_name = "django_control_components/studio/resource_builder.html"

    def get(self, request: HttpRequest, slug: str, *args: Any, **kwargs: Any) -> HttpResponse:
        from django.middleware.csrf import get_token

        spec = _get_spec(slug)
        pal = palette(request)
        table = spec.table or {}
        boot: dict[str, Any] = {
            "doc": {
                "columns": _nodes(table.get("columns")),
                "filters": _nodes(table.get("filters")),
            },
            "palette": pal,
            "revision": spec.revision,
            "listKey": "columns",
            "saveUrl": _url(self.panel, "studio-resource-save", slug=slug),
            "previewUrl": _url(self.panel, "studio-resource-preview", slug=slug),
            "csrfToken": get_token(request),
        }
        return render(
            request,
            self.template_name,
            self.shell_context(
                boot_json=json.dumps(boot),
                spec=spec,
                column_types=pal["columns"],
                filter_types=pal["filters"],
            ),
        )


class ResourceSave(StudioView):
    def post(self, request: HttpRequest, slug: str, *args: Any, **kwargs: Any) -> HttpResponse:
        spec = _get_spec(slug)
        doc = self.read_doc()
        try:
            client_revision = int(request.POST.get("revision", -1))
        except (TypeError, ValueError):
            client_revision = -1
        if client_revision != spec.revision:
            return JsonResponse({"revision": spec.revision, "doc": _current_doc(spec)}, status=409)

        table = dict(spec.table or {})
        table["columns"] = [
            _clean(node) for node in doc.get("columns", []) if isinstance(node, dict)
        ]
        table["filters"] = [
            _clean(node) for node in doc.get("filters", []) if isinstance(node, dict)
        ]

        candidate = {"table": table, "schema": spec.schema, "infolist": spec.infolist}
        try:
            validate_spec(candidate, model=spec.resolve_model(), request=request)
        except ValidationError as exc:
            return JsonResponse(
                {"errors": [{"path": "", "message": str(m)} for m in exc.messages]}, status=422
            )

        spec.table = table
        spec.revision += 1
        spec.save()
        SpecRevision.objects.create(
            dashboard_spec=spec,
            payload={"table": table},
            author=request.user if request.user.is_authenticated else None,
        )
        _trim(spec)
        return JsonResponse({"revision": spec.revision})


class ResourcePreview(StudioView):
    def post(self, request: HttpRequest, slug: str, *args: Any, **kwargs: Any) -> HttpResponse:
        spec = _get_spec(slug)
        doc = self.read_doc()
        model = spec.resolve_model()
        table_spec = {
            "columns": [_clean(n) for n in doc.get("columns", []) if isinstance(n, dict)],
            "filters": [_clean(n) for n in doc.get("filters", []) if isinstance(n, dict)],
        }
        from django.utils.html import escape

        try:
            validate_spec({"table": table_spec}, model=model, request=request)
            table = build_table_from_spec(model._default_manager.all()[:5], table_spec)
            table.client_side()
            body = str(table.render(request))
        except ValidationError as exc:
            detail = escape("; ".join(str(m) for m in exc.messages))
            body = f'<p class="dcc-studio__error">{detail}</p>'
        except Exception as exc:  # a builder edge case must not 500 the preview
            body = f'<p class="dcc-studio__error">{escape(str(exc))}</p>'
        return HttpResponse(body)


# -- helpers -------------------------------------------------------------


def _get_spec(slug: str) -> DashboardSpec:
    try:
        return DashboardSpec.objects.get(slug=slug)
    except DashboardSpec.DoesNotExist:
        raise Http404("no such resource") from None


def _url(panel: Any, name: str, **kwargs: Any) -> str:
    from django.urls import reverse

    return reverse(f"{panel.namespace}:{name}", kwargs=kwargs)


def _nodes(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, node in enumerate(raw or []):
        if not isinstance(node, dict):
            continue
        config = dict(node.get("config") or {})
        if node.get("name"):
            config.setdefault("name", node["name"])
        out.append({"id": f"n{index}", "type": node.get("type", ""), "config": config})
    return out


def _clean(node: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"type": node.get("type", "")}
    config = dict(node.get("config") or {})
    name = config.pop("name", None)
    if name:
        result["name"] = name
    if config:
        result["config"] = config
    return result


def _current_doc(spec: DashboardSpec) -> dict[str, Any]:
    table = spec.table or {}
    return {"columns": _nodes(table.get("columns")), "filters": _nodes(table.get("filters"))}


def _trim(spec: DashboardSpec, keep: int = 20) -> None:
    stale = list(spec.revisions.order_by("-created_at")[keep:].values_list("pk", flat=True))
    if stale:
        SpecRevision.objects.filter(pk__in=stale).delete()
