"""Shared plumbing for the studio builder views."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBase
from django.views import View

from ..access import require_studio

if TYPE_CHECKING:
    from django.http import HttpRequest

    from ...panels.panel import Panel


class StudioView(View):
    """A builder view: gated by ``dcc_studio.use_studio``, anonymous users are
    redirected to login (via the panel's ``LoginRequired`` handling)."""

    panel: Panel

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        from ...panels.guards import LoginRequired

        try:
            if not require_studio(request):
                raise PermissionDenied
        except LoginRequired:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path(), self.panel.get_login_url())
        return super().dispatch(request, *args, **kwargs)

    def shell_context(self, **extra: Any) -> dict[str, Any]:
        from ...panels.nav import build_nav

        ctx = {
            "panel": self.panel,
            "nav": self.panel.navigation(self.request),
            "nav_tree": build_nav(self.panel, self.request),
            "resource_label": "Studio",
        }
        ctx.update(extra)
        return ctx

    def read_doc(self) -> dict[str, Any]:
        raw = self.request.POST.get("doc", "")
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
