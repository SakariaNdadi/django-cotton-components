"""Build a ``Schema`` / ``Table`` / ``Infolist`` from a stored JSON spec.

The spec only ever names a **registered type** (``"TextColumn"``) and passes
**JSON-round-trippable config** to it. Anything else — an import path, a callable,
an unknown setter — raises. Custom behaviour (a ``state`` closure, an action
callback) is not expressible in a spec: it stays in code and is attached by a
``Resource`` subclass after ``from_spec`` builds the declarative shell.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

_SCALAR = (str, int, float, bool, type(None))

# setters that expect a callable / predicate at runtime — never spec-expressible
_UNSAFE_KEYS = frozenset(
    {"state", "state_fn", "action", "callback", "authorize", "visible", "hidden"}
)


def _check_jsonable(value: Any, where: str) -> None:
    if isinstance(value, _SCALAR):
        return
    if isinstance(value, list):
        for item in value:
            _check_jsonable(item, where)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(f"{where}: non-string key {key!r}")
            _check_jsonable(item, where)
        return
    raise ValidationError(f"{where}: {type(value).__name__} is not allowed in a spec")


def _instantiate(registry: Any, node: dict[str, Any], where: str) -> Any:
    if not isinstance(node, dict) or "type" not in node:
        raise ValidationError(f"{where}: each node needs a 'type'")
    type_name = node["type"]
    try:
        cls = registry.get(type_name)
    except KeyError as exc:
        raise ValidationError(str(exc)) from None
    config = node.get("config", {}) or {}
    unsafe = _UNSAFE_KEYS.intersection(config)
    if unsafe:
        raise ValidationError(f"{where}.{type_name}: {sorted(unsafe)} take code, not configuration")
    _check_jsonable(config, f"{where}.{type_name}.config")
    name = node.get("name")
    try:
        component = cls.make(name, **config)
    except TypeError as exc:  # unknown setter / bad arity
        raise ValidationError(f"{where}.{type_name}: {exc}") from None
    return component


def build_schema_from_spec(model: type, spec: dict[str, Any]) -> Any:
    from ..schemas import FIELD_TYPES, Schema

    fields = spec.get("fields")
    schema = Schema.make().model(model, fields=fields) if fields else Schema.make().model(model)

    def walk(nodes: list[dict[str, Any]], where: str) -> list[Any]:
        out = []
        for i, node in enumerate(nodes):
            component = _instantiate(FIELD_TYPES, node, f"{where}[{i}]")
            children = node.get("children")
            if children:
                component.schema(walk(children, f"{where}[{i}].children"))
            out.append(component)
        return out

    layout = spec.get("layout") or spec.get("components")
    if layout:
        schema.schema(walk(layout, "layout"))
    return schema


def build_table_from_spec(queryset: Any, spec: dict[str, Any]) -> Any:
    from ..tables import COLUMN_TYPES, FILTER_TYPES, Table

    table = Table.make(queryset)
    if spec.get("id"):
        table.id(str(spec["id"]))
    columns = [
        _instantiate(COLUMN_TYPES, node, f"columns[{i}]")
        for i, node in enumerate(spec.get("columns", []))
    ]
    table.columns(columns)
    filters = [
        _instantiate(FILTER_TYPES, node, f"filters[{i}]")
        for i, node in enumerate(spec.get("filters", []))
    ]
    if filters:
        table.filters(filters)
    if spec.get("default_sort"):
        table.default_sort(str(spec["default_sort"]))
    if spec.get("page_size"):
        sizes = spec["page_size"]
        table.paginate([int(n) for n in sizes] if isinstance(sizes, list) else [int(sizes)])
    if spec.get("searchable"):
        table.searchable(True)
    return table


def build_infolist_from_spec(model: type, spec: dict[str, Any]) -> Any:
    from ..infolists import ENTRY_TYPES, Infolist

    entries = spec.get("entries")
    if not entries:
        return Infolist.make().model(model)
    built = [_instantiate(ENTRY_TYPES, node, f"entries[{i}]") for i, node in enumerate(entries)]
    return Infolist.make().schema(built)


def validate_spec(spec: dict[str, Any]) -> None:
    """Raise ``ValidationError`` if any table/infolist node is malformed.

    Called from ``DashboardSpec.clean``. Schema layout is validated lazily when a
    model is available (``full_clean`` cannot resolve the model list yet).
    """
    from ..infolists import ENTRY_TYPES
    from ..tables import COLUMN_TYPES, FILTER_TYPES

    for i, node in enumerate((spec.get("table") or {}).get("columns", [])):
        _instantiate(COLUMN_TYPES, node, f"table.columns[{i}]")
    for i, node in enumerate((spec.get("table") or {}).get("filters", [])):
        _instantiate(FILTER_TYPES, node, f"table.filters[{i}]")
    for i, node in enumerate((spec.get("infolist") or {}).get("entries", [])):
        _instantiate(ENTRY_TYPES, node, f"infolist.entries[{i}]")
