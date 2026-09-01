"""Page/layout building blocks - sixth ``TypeRegistry``, alongside
``FIELD_TYPES`` / ``COLUMN_TYPES`` / ``FILTER_TYPES`` / ``ENTRY_TYPES`` /
``WIDGET_TYPES``. A type registered here reaches the studio palette for free
through ``studio/palette.py`` and inherits ``strip_privileged_setters``.
"""

from __future__ import annotations

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
]
