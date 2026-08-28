"""Safe attribute traversal for spec-driven display values.

A column/entry ``name`` such as ``"author.name"`` is walked with ``getattr``.
A stored studio spec is user-editable data, so this walk must never

* reach a private attribute (``_meta``, ``__class__`` internals), or
* auto-invoke a method Django flagged ``alters_data`` (``delete``, ``save``).

Both cases resolve to "no value" — the cell renders empty rather than raising or
mutating a row. This mirrors the Django template language's own ``alters_data``
guard.
"""

from __future__ import annotations

from typing import Any


def traverse(record: Any, path: str) -> Any:
    """Resolve a dotted ``path`` against ``record``, refusing unsafe segments."""
    value: Any = record
    for part in path.split("."):
        if value is None:
            return None
        if not part or part.startswith("_"):
            return None
        value = getattr(value, part, None)
        if callable(value):
            if getattr(value, "alters_data", False):
                return None
            try:
                value = value()
            except TypeError:
                return None
    return value
