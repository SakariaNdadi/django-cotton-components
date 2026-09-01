"""The type palette the studio builder renders as draggable blocks.

One JSON document describing every spec-nameable type and its editable setters,
built from the registries' ``describe_all()``. ``requires="superuser"`` setters
(e.g. ``Column.allow_html``) are stripped for everyone else, so the browser can
never offer them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.http import HttpRequest

    from ..core.type_registry import TypeRegistry


def palette(request: HttpRequest | None = None) -> dict[str, list[dict[str, Any]]]:
    from ..blocks import BLOCK_TYPES
    from ..core.describe import strip_privileged_setters
    from ..infolists import ENTRY_TYPES
    from ..panels import WIDGET_TYPES
    from ..schemas import FIELD_TYPES
    from ..tables import COLUMN_TYPES, FILTER_TYPES

    user = getattr(request, "user", None)
    is_superuser = bool(user is not None and getattr(user, "is_superuser", False))

    def dump(registry: TypeRegistry[Any]) -> list[dict[str, Any]]:
        return [
            strip_privileged_setters(info, is_superuser=is_superuser).as_dict()
            for info in registry.describe_all()
        ]

    return {
        "columns": dump(COLUMN_TYPES),
        "filters": dump(FILTER_TYPES),
        "fields": dump(FIELD_TYPES),
        "entries": dump(ENTRY_TYPES),
        "widgets": dump(WIDGET_TYPES),
        "blocks": dump(BLOCK_TYPES),
    }
