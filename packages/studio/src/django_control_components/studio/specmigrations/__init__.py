"""Versioned migrations for stored spec-document JSON.

The thing that keeps a no-code tool alive across releases: when the block IR's
shape changes, a stored document does not have to change with it on every
deploy. Each migration upgrades a document by exactly one ``schema_version``,
applied on **read** — an old row keeps resolving under the version it was
written with, and is rewritten to the current shape lazily the next time it is
saved. Mirrors Django's own migration shape (ordered, forward-only, one step at
a time) rather than inventing a new one.

No migrations are registered yet — nothing stores a document in the
``{"schema_version": n, "root": {...}}`` envelope this targets until the
layout/chrome blocks and the ``Page`` model exist. This module is the
mechanism; ``migrate()`` on an empty registry is a no-op passthrough, exercised
by tests with locally-constructed :class:`SpecMigration` instances so a test
never has to touch the process-global registry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Forward = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class SpecMigration:
    #: the schema_version a document has *after* this migration runs
    version: int
    #: short slug for error messages / the audit trail, e.g. "flat_to_blocks"
    name: str
    forward: Forward


#: production migrations, registered in ascending version order via `register()`
_REGISTRY: list[SpecMigration] = []


def register(version: int, name: str) -> Callable[[Forward], Forward]:
    """Decorator: ``@register(1, "flat_to_blocks")`` on a ``forward(doc) -> doc``
    function. Registration order does not matter — ``migrate()`` always applies
    by ascending ``version``."""

    def decorator(fn: Forward) -> Forward:
        _REGISTRY.append(SpecMigration(version=version, name=name, forward=fn))
        _REGISTRY.sort(key=lambda m: m.version)
        return fn

    return decorator


def current_version(migrations: list[SpecMigration] | None = None) -> int:
    registry = _REGISTRY if migrations is None else migrations
    return registry[-1].version if registry else 0


def migrate(
    doc: dict[str, Any], *, migrations: list[SpecMigration] | None = None
) -> dict[str, Any]:
    """Upgrade ``doc`` to ``current_version()``, applying every migration newer
    than its own ``schema_version`` in order. Never mutates the input; a
    document with no ``schema_version`` is treated as version 0."""
    registry = _REGISTRY if migrations is None else sorted(migrations, key=lambda m: m.version)
    doc = dict(doc)
    have = int(doc.get("schema_version", 0))
    for step in registry:
        if step.version > have:
            doc = step.forward(doc)
            doc["schema_version"] = step.version
    return doc


__all__ = ["SpecMigration", "current_version", "migrate", "register"]
