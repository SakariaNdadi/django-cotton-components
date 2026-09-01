"""A single Django-admin entry that opens the standalone studio.

Auto-imported by ``django.contrib.admin`` autodiscovery — so this module is only
loaded when the admin is installed. Gated by ``DCC["STUDIO_ADMIN_ENTRY"]``.
"""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from ..conf import dcc_settings
from .access import can_use_studio
from .models import StudioEntry

if dcc_settings.STUDIO_ADMIN_ENTRY:

    @admin.register(StudioEntry)
    class StudioEntryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
        """Renders nothing — every entry point redirects to ``dcc_studio:home``."""

        def has_module_permission(self, request: HttpRequest) -> bool:
            return can_use_studio(request)

        def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
            return can_use_studio(request)

        def has_add_permission(self, request: HttpRequest) -> bool:
            return False

        def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
            return False

        def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
            return False

        def changelist_view(
            self, request: HttpRequest, extra_context: dict[str, Any] | None = None
        ) -> HttpResponse:
            return redirect("dcc_studio:home")
