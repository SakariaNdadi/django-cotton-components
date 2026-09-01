"""Compile a small, safe predicate DSL to an Alpine expression.

Only these forms are supported; anything else must use ``.reactive()`` (a server
round-trip) or a plain Python closure (evaluated once at render, not reactive):

    .visible_when("type", equals="other")
    .visible_when("kind", is_in=["a", "b"])
    .visible_when("accept_terms")            # truthy

The generated expression reads sibling controls by ``name`` through a helper the
schema wrapper installs on the Alpine root scope (``$dccField``) — so this only
does anything inside a ``.dcc-form`` (a rendered ``Schema``), on a ``Field`` or a
``Layout`` container.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VisibilityRule:
    field: str
    equals: Any = None
    is_in: tuple[Any, ...] | None = None
    truthy: bool = False

    def to_alpine(self) -> str:
        ref = f"$dccField({json.dumps(self.field)})"
        if self.is_in is not None:
            return f"{json.dumps(list(self.is_in))}.includes({ref})"
        if self.truthy:
            return f"!!{ref}"
        return f"{ref} == {json.dumps(self.equals)}"
