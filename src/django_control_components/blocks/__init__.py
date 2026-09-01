"""Page/layout building blocks — sixth ``TypeRegistry``, alongside
``FIELD_TYPES`` / ``COLUMN_TYPES`` / ``FILTER_TYPES`` / ``ENTRY_TYPES`` /
``WIDGET_TYPES``. A type registered here reaches the studio palette for free
through ``studio/palette.py`` and inherits ``strip_privileged_setters``.

Empty until the layout/chrome blocks (``AppShell``, ``Grid``, ``Sidebar``, …)
register into it.
"""

from __future__ import annotations

from ..core.type_registry import TypeRegistry
from .base import Block

BLOCK_TYPES: TypeRegistry[Block] = TypeRegistry("block")

__all__ = ["BLOCK_TYPES", "Block"]
