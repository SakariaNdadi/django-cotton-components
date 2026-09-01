"""Page/layout building blocks - sixth ``TypeRegistry``, alongside
``FIELD_TYPES`` / ``COLUMN_TYPES`` / ``FILTER_TYPES`` / ``ENTRY_TYPES`` /
``WIDGET_TYPES``. A type registered here reaches the studio palette for free
through ``studio/palette.py`` and inherits ``strip_privileged_setters``.
"""

from __future__ import annotations

from collections.abc import Callable

from ..core.type_registry import TypeRegistry
from .base import Block
from .chrome import AppShell, Footer, Navbar, NotificationBell, Sidebar
from .layout import Card, Column, Divider, Grid, Row, Spacer, Stack

BLOCK_TYPES: TypeRegistry[Block] = TypeRegistry("block")

for _cls, _label, _icon, _slots in (
    (Stack, "Stack", "bars-staggered", ("default",)),
    (Row, "Row", "grip-lines-vertical", ("default",)),
    (Grid, "Grid", "table-cells", ("default",)),
    (Column, "Column", "table-columns", ("default",)),
    (Card, "Card", "square", ("header", "body", "footer")),
    (Divider, "Divider", "minus", ()),
    (Spacer, "Spacer", "up-down", ()),
    (AppShell, "App shell", "window-maximize", ("topbar", "sidebar", "content", "footer")),
    (Navbar, "Navbar", "window-minimize", ("start", "end")),
    (Sidebar, "Sidebar", "table-columns", ("default",)),
    (Footer, "Footer", "window-minimize", ("default",)),
    (NotificationBell, "Notification bell", "bell", ()),
):
    BLOCK_TYPES.register(
        _cls, label=_label, icon=_icon, category="block", accepts_children=bool(_slots)
    )


def block(
    label: str | None = None,
    *,
    name: str | None = None,
    icon: str = "",
    category: str = "block",
) -> Callable[[type[Block]], type[Block]]:
    """Class decorator: register a custom :class:`Block` so it is draggable in
    the studio palette immediately — the sugar form of ``BLOCK_TYPES.register``.

        @block("Callout", icon="bullhorn")
        class Callout(Block):
            slots = ("default",)
            template_name = "myapp/blocks/callout.html"
    """

    def decorate(cls: type[Block]) -> type[Block]:
        BLOCK_TYPES.register(
            cls,
            name=name,
            label=label,
            icon=icon,
            category=category,
            accepts_children=bool(getattr(cls, "slots", ())),
        )
        return cls

    return decorate


__all__ = [
    "BLOCK_TYPES",
    "AppShell",
    "Block",
    "Card",
    "Column",
    "Divider",
    "Footer",
    "Grid",
    "Navbar",
    "NotificationBell",
    "Row",
    "Sidebar",
    "Spacer",
    "Stack",
    "block",
]
