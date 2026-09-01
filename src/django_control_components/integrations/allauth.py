"""django-allauth integration - route a signed-in user to their studio home.

Enable with ``pip install "django-control-components[allauth]"`` and, in settings::

    ACCOUNT_ADAPTER = "django_control_components.integrations.allauth.DCCAccountAdapter"
    DCC = {"HOME_PANEL": "admin"}   # Panel.name whose home to resolve

The adapter falls back to allauth's own ``LOGIN_REDIRECT_URL`` behaviour when no
panel is configured or the panel cannot be found, so it is safe to set
unconditionally. Importing this module without allauth installed raises
``ImproperlyConfigured`` - the rest of the library is unaffected.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured

try:
    from allauth.account.adapter import DefaultAccountAdapter
    from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
except ImportError as exc:  # pragma: no cover - exercised via importorskip
    raise ImproperlyConfigured(
        'django-allauth is not installed. Run: pip install "django-control-components[allauth]"'
    ) from exc


def _studio_home(request: Any) -> str | None:
    from ..conf import dcc_settings

    panel_name = dcc_settings.HOME_PANEL
    if not panel_name:
        return None
    panel = _find_panel(panel_name)
    if panel is None:
        return None
    try:
        from ..studio.home import resolve_home
    except ModuleNotFoundError:
        return None

    try:
        return resolve_home(request, panel)
    except Exception:
        return None


def _find_panel(name: str) -> Any:
    """Locate a mounted ``Panel`` by name by walking the root URLconf once."""
    from django.urls import get_resolver

    from ..panels.panel import Panel

    seen: list[Any] = []

    def walk(patterns: Any) -> None:
        for entry in patterns:
            handler = getattr(entry, "url_patterns", None)
            if handler is not None:
                walk(handler)
            callback = getattr(entry, "callback", None)
            panel = getattr(callback, "__self__", None)
            if isinstance(panel, Panel):
                seen.append(panel)

    try:
        walk(get_resolver().url_patterns)
    except Exception:
        return None
    return next((p for p in seen if p.name == name), None)


class DCCAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request: Any) -> str:
        return _studio_home(request) or str(super().get_login_redirect_url(request))


class DCCSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request: Any, socialaccount: Any) -> str:
        return _studio_home(request) or str(
            super().get_connect_redirect_url(request, socialaccount)
        )
