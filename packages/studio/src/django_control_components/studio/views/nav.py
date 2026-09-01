"""The sidebar builder: palette of nav-item kinds, a sortable canvas, an
inspector, save (full-document rebuild) and live preview."""

from __future__ import annotations

import json
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from ..models import NavDocument, NavItem
from .base import StudioView

_KINDS = [{"kind": kind, "label": label} for kind, label in NavItem.Kind.choices]

#: fields the nav builder owns and may overwrite on an existing row. Access-matrix
#: fields (``required_permission``, ``groups``, ``users``) are edited in RolesView
#: and are deliberately left untouched here.
_BUILDER_FIELDS = ("label", "icon", "target_kind", "target", "is_enabled", "open_in_new_tab")


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
            "revision": _revision_of(self.panel.name),
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

        panel_name = self.panel.name
        try:
            client_revision = int(request.POST.get("revision", -1))
        except (TypeError, ValueError):
            client_revision = -1

        with transaction.atomic():
            navdoc, _ = NavDocument.objects.select_for_update().get_or_create(panel=panel_name)
            if client_revision != navdoc.revision:
                return JsonResponse(
                    {
                        "revision": navdoc.revision,
                        "doc": {"items": _current_items(panel_name)},
                    },
                    status=409,
                )
            try:
                _apply(panel_name, items)
            except ValidationError as exc:
                return _error_response(list(exc.messages))
            navdoc.revision += 1
            navdoc.save(update_fields=["revision", "updated_at"])

        return JsonResponse({"revision": navdoc.revision})


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
        "is_enabled": row.is_enabled,
        "open_in_new_tab": row.open_in_new_tab,
        "is_public": row.is_public,
    }


def _revision_of(panel_name: str) -> int:
    row = NavDocument.objects.filter(panel=panel_name).values_list("revision", flat=True).first()
    return row or 0


def _apply(panel_name: str, items: list[Any]) -> None:
    """Reconcile the panel's nav rows against ``items`` by client id.

    Existing rows (``id`` = ``"db<pk>"``) are updated in place — so
    access-matrix fields set in RolesView survive. Rows missing from the payload
    are deleted; new items are created. Two levels deep, folded under the most
    recent ``group`` item exactly as before.
    """
    existing = {row.pk: row for row in NavItem.objects.filter(panel=panel_name)}
    seen_pks: set[int] = set()
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

        pk = _pk_from_id(raw.get("id"))
        row = existing.get(pk) if pk is not None else None
        if row is None:
            row = NavItem(panel=panel_name)

        row.label = label
        row.icon = (raw.get("icon") or "").strip()
        row.target_kind = kind
        row.target = (raw.get("target") or "").strip()
        row.is_enabled = bool(raw.get("is_enabled", True))
        row.open_in_new_tab = bool(raw.get("open_in_new_tab", False))
        row.order = order
        row.parent = None if kind == NavItem.Kind.GROUP else current_group
        row.save()
        seen_pks.add(row.pk)
        if kind == NavItem.Kind.GROUP:
            current_group = row

    stale = set(existing) - seen_pks
    if stale:
        NavItem.objects.filter(pk__in=stale).delete()


def _pk_from_id(raw_id: Any) -> int | None:
    if isinstance(raw_id, str) and raw_id.startswith("db"):
        try:
            return int(raw_id[2:])
        except ValueError:
            return None
    return None


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
