"""Font Awesome icon set (free tier).

Names are ``"<style>:<icon>"`` or just ``"<icon>"`` (defaults to the ``solid``
style). ``"pen"`` -> ``<i class="fa-solid fa-pen"></i>``,
``"brands:github"`` -> ``<i class="fa-brands fa-github"></i>``.
"""

from __future__ import annotations

import re

from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

_STYLES = {"solid", "regular", "light", "thin", "duotone", "brands"}
_TOKEN = re.compile(r"\A[a-z0-9-]+\Z")

_CDN = "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.7.2/css/all.min.css"


class FontAwesome:
    def __init__(self, asset_url: str | None = _CDN) -> None:
        self.asset_url = asset_url

    def _split(self, name: str) -> tuple[str, str]:
        style, _, icon = name.partition(":")
        if not icon:
            style, icon = "solid", style
        if style not in _STYLES:
            style, icon = "solid", name
        return style, icon

    def render(self, name: str, *, css_class: str = "") -> SafeString:
        style, icon = self._split(name.strip())
        if not _TOKEN.match(icon):
            return SafeString("")
        classes = f"fa-{style} fa-{icon}"
        if css_class:
            classes = f"{classes} {css_class}"
        return format_html('<i class="{}" aria-hidden="true"></i>', classes)

    def assets(self) -> SafeString:
        if not self.asset_url:
            return SafeString("")
        return mark_safe(  # noqa: S308  -- setting-controlled URL, fixed markup
            f'<link rel="stylesheet" href="{self.asset_url}">'
        )
