"""The sidebar builder: palette of nav-item kinds, a sortable canvas, an
inspector, save (full-document rebuild) and live preview."""

from __future__ import annotations

import json
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from ..models import NavItem
from .base import StudioView

_KINDS = [{"kind": kind, "label": label} for kind, label in NavItem.Kind.choices]


class StudioHome(StudioView):
    template_name = "django_control_components/studio/home.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, self.shell_context())


class NavBuilder(StudioView):
    template_name = "django_control_components/studio/nav_builder.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        from django.middleware.csrf import get_token

        boot = {
            "doc": {"items": _current_items(self.panel.name)},
            "kinds": _KINDS,
            "revision": 0,
            "saveUrl": _url(self.panel, "studio-nav-save"),
            "previewUrl": _url(self.panel, "studio-nav-preview"),
            "csrfToken": get_token(request),
        }
        return render(
            request,
            self.template_name,
            self.shell_context(boot_json=json.dumps(boot), kinds=_KINDS),
        )


class NavSave(StudioView):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        doc = self.read_doc()
        items = doc.get("items", [])
        if not isinstance(items, list):
            return _error_response(["items: expected a list"])

        try:
            with transaction.atomic():
                NavItem.objects.filter(panel=self.panel.name).delete()
                _rebuild(self.panel.name, items)
        except ValidationError as exc:
            return _error_response(list(exc.messages))

        return JsonResponse({"revision": 1})


class NavPreview(StudioView):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        doc = self.read_doc()
        tree = _preview_tree(doc.get("items", []))
        return render(
            request,
            "django_control_components/panels/_nav.html",
            {"panel": self.panel, "nav_tree": tree, "request": request},
        )


# -- helpers ---------------------------------------------------------------


def _url(panel: Any, name: str) -> str:
    from django.urls import reverse

    return reverse(f"{panel.namespace}:{name}")


def _current_items(panel_name: str) -> list[dict[str, Any]]:
    rows = NavItem.objects.filter(panel=panel_name).order_by("order", "pk")
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.parent_id is not None:
            continue
        out.append(_row_to_item(row))
        for child in rows.filter(parent_id=row.pk):
            out.append(_row_to_item(child))
    return out


def _row_to_item(row: NavItem) -> dict[str, Any]:
    return {
        "id": f"db{row.pk}",
        "label": row.label,
        "icon": row.icon,
        "target": row.target,
        "target_kind": row.target_kind,
        "is_public": row.is_public,
    }


def _rebuild(panel_name: str, items: list[Any]) -> None:
    current_group: NavItem | None = None
    for order, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise ValidationError("each nav item must be an object")
        kind = raw.get("target_kind", "url")
        label = (raw.get("label") or "").strip()
        if not label:
            raise ValidationError("every nav item needs a label")
        if kind not in NavItem.Kind.values:
            raise ValidationError(f"unknown nav kind {kind!r}")

        item = NavItem(
            panel=panel_name,
            label=label,
            icon=(raw.get("icon") or "").strip(),
            order=order,
            target_kind=kind,
            target=(raw.get("target") or "").strip(),
            is_public=bool(raw.get("is_public", True)),
        )
        if kind == NavItem.Kind.GROUP:
            item.save()
            current_group = item
        else:
            item.parent = current_group
            item.save()


def _preview_tree(items: list[Any]) -> list[Any]:
    from ...panels.nav import NavNode
    from ..models import NavItem as _NavItem

    nodes: list[NavNode] = []
    group: NavNode | None = None
    for raw in items:
        if not isinstance(raw, dict):
            continue
        kind = raw.get("target_kind", "url")
        label = (raw.get("label") or "").strip() or "—"
        if kind == _NavItem.Kind.GROUP:
            group = NavNode(label=label)
            nodes.append(group)
            continue
        node = NavNode(label=label, url=(raw.get("target") or "#"), icon=raw.get("icon", ""))
        (group.children if group is not None else nodes).append(node)
    return nodes


def _error_response(messages: list[str]) -> JsonResponse:
    return JsonResponse({"errors": [{"path": "", "message": str(m)} for m in messages]}, status=422)
