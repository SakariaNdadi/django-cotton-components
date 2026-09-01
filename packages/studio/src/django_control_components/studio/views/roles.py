"""Access overview — which groups a studio object is visible to, with quick
toggles. Superuser only; raw group / permission management stays in django
admin. Never the generic spec builder (``auth.Group`` is on the model deny
list)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from ..models import AccessControlled, DashboardSpec, NavItem, PanelDashboard, Visibility
from .base import StudioView

_MODELS: dict[str, type[AccessControlled]] = {
    "spec": DashboardSpec,
    "dashboard": PanelDashboard,
    "nav": NavItem,
}


class RolesView(StudioView):
    template_name = "django_control_components/studio/roles.html"
    active_section = "roles"

    def _require_superuser(self, request: HttpRequest) -> None:
        user = getattr(request, "user", None)
        if not (user and user.is_superuser):
            raise PermissionDenied("Users & Roles is superuser-only.")

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self._require_superuser(request)
        groups = list(Group.objects.order_by("name"))
        rows = []
        for kind, model in _MODELS.items():
            for obj in model._default_manager.all():
                rows.append(
                    {
                        "kind": kind,
                        "pk": obj.pk,
                        "label": str(obj),
                        "visibility": obj.visibility,
                        "group_ids": set(obj.groups.values_list("pk", flat=True)),
                    }
                )
        return render(
            request,
            self.template_name,
            self.shell_context(groups=groups, rows=rows, visibilities=Visibility.choices),
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self._require_superuser(request)
        kind = request.POST.get("kind", "")
        model = _MODELS.get(kind)
        pk = request.POST.get("pk") or ""
        if model is None or not pk.isdigit():
            raise PermissionDenied("bad object reference")
        obj = model._default_manager.filter(pk=int(pk)).first()
        if obj is None:
            raise PermissionDenied("no such object")

        action = request.POST.get("action")
        if action == "set_visibility":
            value = request.POST.get("visibility", "")
            if value in Visibility.values:
                obj.visibility = value
                obj.save(update_fields=["visibility"])
        elif action in ("grant", "revoke"):
            group_pk = request.POST.get("group") or ""
            group = Group.objects.filter(pk=int(group_pk)).first() if group_pk.isdigit() else None
            if group is not None:
                (obj.groups.add if action == "grant" else obj.groups.remove)(group)
        return redirect("dcc_studio:roles")
