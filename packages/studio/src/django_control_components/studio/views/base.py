"""Shared plumbing for the studio builder views.

The studio is mounted at its own URL (``include("django_control_components.studio.urls")``),
not under a panel, so these views carry no ``panel`` — a panel is a *parameter*
of the artefact being edited (only the nav builder needs one).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBase
from django.views import View

from ..access import require_studio

if TYPE_CHECKING:
    from django.http import HttpRequest


class StudioView(View):
    """A builder view: gated by ``dcc_studio.use_studio``; anonymous users are
    redirected to ``settings.LOGIN_URL``."""

    #: drives the active state in the studio's own sidebar
    active_section: str = ""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        from ...panels.guards import LoginRequired

        try:
            if not require_studio(request):
                raise PermissionDenied
        except LoginRequired:
            from django.conf import settings
            from django.contrib.auth.views import redirect_to_login

            login_url = getattr(settings, "LOGIN_URL", None) or "/accounts/login/"
            return redirect_to_login(request.get_full_path(), str(login_url))
        return super().dispatch(request, *args, **kwargs)

    def shell_context(self, **extra: Any) -> dict[str, Any]:
        from ...panels.panel import all_panels

        ctx: dict[str, Any] = {
            "studio_panels": [p for p in all_panels() if getattr(p, "_studio", False)],
            "active": self.active_section,
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
