"""Settings shim.

Consumers configure the library through a single ``DCC`` dict in their Django
settings. Access values via ``dcc_settings`` so defaults live in exactly one
place and a typo in a key raises instead of silently returning ``None``.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

DEFAULTS: dict[str, Any] = {
    # Tables render client-side (zero requests) at or below this row count.
    "TABLE_CLIENT_SIDE_MAX_ROWS": 200,
    # Page-size options offered by table pagination.
    "TABLE_PER_PAGE_CHOICES": [10, 25, 50, 100],
    # Debounce (ms) applied to opt-in live field validation.
    "LIVE_VALIDATION_DEBOUNCE_MS": 400,
    # Pillow decompression-bomb ceiling for uploaded images.
    "IMAGE_MAX_PIXELS": 24_000_000,
    # Dotted path to the thumbnail backend. None => auto-detect.
    "THUMBNAIL_BACKEND": None,
    # Prefix for htmx-driven internal endpoints (schemas, actions).
    "URL_PREFIX": "dcc/",
    # Dotted path to the active icon set.
    "ICON_SET": "django_control_components.icons.FontAwesome",
    # Icon stylesheet URL. None => the set self-hosts / emits nothing.
    "ICON_ASSET_URL": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.7.2/css/all.min.css",
    # Models a stored studio spec may aggregate over (``"app_label.Model"``). A
    # widget's ``.query({...})`` refuses any model not in this list.
    "STUDIO_MODELS": [],
    # Models the studio's resource / scaffold picker may target. ``None`` => every
    # installed model except the built-in sensitive set; a list => exactly those
    # (``"app_label.Model"``). The picker also intersects ``view_`` permission.
    "STUDIO_RESOURCE_MODELS": None,
    # Alias -> dotted path map for the studio escape hatch. A spec references a
    # predicate by ``"@alias"`` on a ``visible`` / ``hidden`` config key; it can
    # never name an import path directly.
    "STUDIO_CALLABLES": {},
    # ``Panel.name`` whose home the allauth adapter resolves after login. None =>
    # fall back to allauth's own ``LOGIN_REDIRECT_URL``.
    "HOME_PANEL": None,
    # Show a "Studio" entry in the Django admin index (redirects to the standalone
    # studio hub). Set False if the project does not use django.contrib.admin or
    # wants its own entry point. Requires the studio URLs to be mounted.
    "STUDIO_ADMIN_ENTRY": True,
    # Serve htmx / Alpine / the focus plugin from the project's own static files
    # instead of a CDN. Air-gapped and privacy-sensitive deploys set this True and
    # place the pinned files under ``VENDOR_ASSET_DIR`` (``manage.py dcc_vendor_assets``
    # fetches them).
    "VENDOR_ASSETS": False,
    # Static path prefix the vendored copies live under when ``VENDOR_ASSETS``.
    "VENDOR_ASSET_DIR": "dcc/vendor/",
    # Optional Subresource Integrity map, ``{cdn_url: "sha384-..."}``. Any CDN asset
    # URL present here is emitted with ``integrity`` + ``crossorigin="anonymous"``.
    "ASSET_SRI": {},
    # When True, an ``Action`` with no ``.authorize()`` rule is denied instead of
    # allowed. Safer default for teams that treat every action as privileged;
    # left False so existing code is not silently locked out on upgrade.
    "ACTIONS_DEFAULT_DENY": False,
}


class _Settings:
    def __getattr__(self, name: str) -> Any:
        if name not in DEFAULTS:
            raise AttributeError(f"Unknown DCC setting: {name!r}. Valid keys: {sorted(DEFAULTS)}")
        user = getattr(settings, "DCC", {})
        return user.get(name, DEFAULTS[name])


dcc_settings = _Settings()


@receiver(setting_changed)
def _reset_on_change(*, setting: str, **kwargs: Any) -> None:
    # _Settings reads live each access, but the icon registry memoises the
    # resolved set, so drop that cache when DCC changes under override_settings.
    if setting == "DCC":
        from .icons.registry import _reset_cache

        _reset_cache()
