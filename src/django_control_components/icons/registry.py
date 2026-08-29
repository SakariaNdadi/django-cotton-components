"""Resolve the active icon set and render through it.

The set is chosen by ``DCC["ICON_SET"]`` (a dotted path); ``DCC["ICON_ASSET_URL"]``
overrides the stylesheet URL (``None`` to self-host and emit nothing).
"""

from __future__ import annotations

from functools import lru_cache

from django.utils.module_loading import import_string
from django.utils.safestring import SafeString

from ..conf import dcc_settings
from .base import IconSet


@lru_cache(maxsize=1)
def _active_set(dotted: str, asset_url: str | None) -> IconSet:
    cls = import_string(dotted)
    try:
        return cls(asset_url=asset_url)
    except TypeError:
        return cls()


def active_set() -> IconSet:
    return _active_set(dcc_settings.ICON_SET, dcc_settings.ICON_ASSET_URL)


def render_icon(name: str | None, *, css_class: str = "") -> SafeString:
    if not name:
        return SafeString("")
    return active_set().render(name, css_class=css_class)


def icon_assets() -> SafeString:
    return active_set().assets()


def _reset_cache() -> None:
    _active_set.cache_clear()
