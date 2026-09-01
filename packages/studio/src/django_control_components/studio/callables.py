"""The 10% escape hatch: a spec references Python behaviour by **alias**, never
by import path.

    DCC = {"STUDIO_CALLABLES": {"is_overdue": "myapp.rules.is_overdue"}}

A spec then writes ``{"config": {"visible": "@is_overdue"}}``. Only ``visible`` /
``hidden`` accept an alias (they take a simple predicate); ``state`` / ``action``
/ ``authorize`` stay code-only. An unregistered alias raises ``ValidationError``,
so a spec editor can never name an arbitrary importable.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.utils.module_loading import import_string

#: config keys that may carry an ``@alias`` string
#: config keys whose value may be an ``@alias`` string resolved through
#: ``DCC["STUDIO_CALLABLES"]`` to a project callable. ``visible`` / ``hidden``
#: are predicates; ``label`` / ``url`` are value producers. ``authorize`` is
#: deliberately absent and can never be added — a stored spec must not name the
#: callable that decides access.
ALIASABLE_KEYS = frozenset({"visible", "hidden", "label", "url"})


def is_alias(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("@") and len(value) > 1


def resolve_alias(value: str) -> Any:
    from ..conf import dcc_settings

    name = value[1:]
    registry: dict[str, str] = dict(dcc_settings.STUDIO_CALLABLES)
    if name not in registry:
        raise ValidationError(
            f"{value!r}: not a registered DCC['STUDIO_CALLABLES'] alias "
            f"({sorted(registry) or 'none configured'})"
        )
    try:
        resolved = import_string(registry[name])
    except ImportError as exc:
        raise ValidationError(
            f"{value!r}: alias {registry[name]!r} will not import: {exc}"
        ) from None
    if not callable(resolved):
        raise ValidationError(f"{value!r}: alias {registry[name]!r} is not callable")
    return resolved


def resolve_config_aliases(config: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``config`` with any ``@alias`` value on an aliasable key
    replaced by the resolved callable."""
    if not any(is_alias(config.get(key)) for key in ALIASABLE_KEYS):
        return config
    resolved = dict(config)
    for key in ALIASABLE_KEYS:
        if is_alias(resolved.get(key)):
            resolved[key] = resolve_alias(resolved[key])
    return resolved
