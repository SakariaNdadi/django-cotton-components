"""Icon-set protocol.

An icon set turns a short name (``"pen"``, ``"solid:trash"``) into a small
chunk of safe HTML, and knows what stylesheet/script the page needs for that
HTML to render. Swapping Font Awesome for another set is a one-line setting.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from django.utils.safestring import SafeString


@runtime_checkable
class IconSet(Protocol):
    def render(self, name: str, *, css_class: str = "") -> SafeString:
        """Return the icon markup for ``name`` (already safe)."""
        ...

    def assets(self) -> SafeString:
        """Return any ``<link>`` / ``<script>`` tags the markup depends on."""
        ...
