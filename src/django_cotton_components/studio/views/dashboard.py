"""The dashboard builder: a palette of widget types, a reorderable canvas, a
palette-driven inspector, revision-guarded save and a live preview."""

from __future__ import annotations

import json
from typing import Any

from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.utils.text import slugify

from ..deserialize import build_widgets_from_spec, validate_widgets_spec
from ..models import PanelDashboard, SpecRevision
from ..palette import palette
from .base import StudioView


class DashboardIndex(StudioView):
    template_name = "django_cotton_components/studio/dashboard_index.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(
            request,
            self.template_name,
            self.shell_context(dashboards=list(PanelDashboard.objects.order_by("slug"))),
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        label = (request.POST.get("label") or "").strip()
        if not label:
            return render(
                request,
                self.template_name,
                self.shell_context(
                    dashboards=list(PanelDashboard.objects.order_by("slug")),
                    error="A name is required.",
                ),
            )
        dashboard = PanelDashboard(label=label, slug=slugify(label), widgets=[])
        dashboard.save()
        return redirect(f"{self.panel.namespace}:studio-dash", slug=dashboard.slug)


class DashboardBuilder(StudioView):
    template_name = "django_cotton_components/studio/dashboard_builder.html"

    def get(self, request: HttpRequest, slug: str, *args: Any, **kwargs: Any) -> HttpResponse:
        from django.middleware.csrf import get_token

        dashboard = _get_dashboard(slug)
        pal = palette(request)
        boot: dict[str, Any] = {
            "doc": {"items": _items(dashboard)},
            "palette": pal,
            "revision": dashboard.revision,
            "saveUrl": _url(self.panel, "studio-dash-save", slug=slug),
            "previewUrl": _url(self.panel, "studio-dash-preview", slug=slug),
            "csrfToken": get_token(request),
        }
        return render(
            request,
            self.template_name,
            self.shell_context(
                boot_json=json.dumps(boot),
                dashboard=dashboard,
                widget_types=pal["widgets"],
            ),
        )


class DashboardSave(StudioView):
    def post(self, request: HttpRequest, slug: str, *args: Any, **kwargs: Any) -> HttpResponse:
        dashboard = _get_dashboard(slug)
        doc = self.read_doc()
        try:
            client_revision = int(request.POST.get("revision", -1))
        except (TypeError, ValueError):
            client_revision = -1
        if client_revision != dashboard.revision:
            return JsonResponse(
                {"revision": dashboard.revision, "doc": {"items": _items(dashboard)}}, status=409
            )

        widgets = [_clean_node(node) for node in doc.get("items", []) if isinstance(node, dict)]
        try:
            validate_widgets_spec(widgets)
        except ValidationError as exc:
            return JsonResponse(
                {"errors": [{"path": "", "message": str(m)} for m in exc.messages]}, status=422
            )

        dashboard.widgets = widgets
        dashboard.revision += 1
        dashboard.save()
        SpecRevision.objects.create(
            panel_dashboard=dashboard,
            payload={"widgets": widgets},
            author=request.user if request.user.is_authenticated else None,
        )
        _trim_revisions(dashboard)
        return JsonResponse({"revision": dashboard.revision})


class DashboardPreview(StudioView):
    def post(self, request: HttpRequest, slug: str, *args: Any, **kwargs: Any) -> HttpResponse:
        _get_dashboard(slug)
        doc = self.read_doc()
        widgets = [_clean_node(n) for n in doc.get("items", []) if isinstance(n, dict)]
        try:
            validate_widgets_spec(widgets)
            built = build_widgets_from_spec(widgets)
            body = "".join(str(w.render(request)) for w in built)
        except ValidationError as exc:
            message = escape("; ".join(str(m) for m in exc.messages))
            body = f'<p class="dcc-studio__error">{message}</p>'
        # `body` is already-safe widget HTML (or an escaped error); the wrapper
        # is a fixed string, so no marking is required.
        return HttpResponse(f'<div class="dcc-widgets">{body}</div>')


# -- helpers -------------------------------------------------------------


def _get_dashboard(slug: str) -> PanelDashboard:
    try:
        return PanelDashboard.objects.get(slug=slug)
    except PanelDashboard.DoesNotExist:
        raise Http404("no such dashboard") from None


def _url(panel: Any, name: str, **kwargs: Any) -> str:
    from django.urls import reverse

    return reverse(f"{panel.namespace}:{name}", kwargs=kwargs)


def _items(dashboard: PanelDashboard) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, node in enumerate(dashboard.widgets or []):
        if not isinstance(node, dict):
            continue
        out.append(
            {
                "id": f"w{index}",
                "type": node.get("type", ""),
                "config": {k: v for k, v in node.items() if k not in ("type", "id")},
            }
        )
    return out


def _clean_node(node: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"type": node.get("type", "")}
    config = node.get("config") or {}
    if isinstance(config, dict):
        if config.get("name"):
            result["name"] = config["name"]
        payload = {k: v for k, v in config.items() if k != "name"}
        if payload:
            result["config"] = payload
    return result


def _trim_revisions(dashboard: PanelDashboard, keep: int = 20) -> None:
    stale = dashboard.revisions.order_by("-created_at")[keep:].values_list("pk", flat=True)
    if stale:
        SpecRevision.objects.filter(pk__in=list(stale)).delete()
