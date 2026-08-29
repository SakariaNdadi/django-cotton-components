"""Build a ``Schema`` / ``Table`` / ``Infolist`` from a stored JSON spec.

The spec only ever names a **registered type** (``"TextColumn"``) and passes
**JSON-round-trippable config** to it. Anything else — an import path, a callable,
an unknown setter — raises. Custom behaviour (a ``state`` closure, an action
callback) is not expressible in a spec: it stays in code and is attached by a
``Resource`` subclass after ``from_spec`` builds the declarative shell.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.exceptions import FieldDoesNotExist, ValidationError

from ..core.describe import CODE_ONLY_SETTERS

_SCALAR = (str, int, float, bool, type(None))

#: hard ceilings applied to a stored spec before it is walked — a spec is
#: user-editable data, so an unbounded document must not reach the builders.
_MAX_SPEC_BYTES = 64 * 1024
_MAX_SPEC_DEPTH = 8

# setters that expect a callable / predicate at runtime — never spec-expressible.
# Canonical set now lives in core.describe; alias kept for one release.
_UNSAFE_KEYS = CODE_ONLY_SETTERS


def _check_size_and_depth(spec: Any) -> None:
    try:
        encoded = json.dumps(spec)
    except (TypeError, ValueError):
        raise ValidationError("spec is not JSON-serialisable") from None
    if len(encoded.encode("utf-8")) > _MAX_SPEC_BYTES:
        raise ValidationError(f"spec exceeds the {_MAX_SPEC_BYTES // 1024} KB ceiling")

    def _depth(node: Any, level: int) -> None:
        if level > _MAX_SPEC_DEPTH:
            raise ValidationError(f"spec nesting exceeds {_MAX_SPEC_DEPTH} levels")
        if isinstance(node, dict):
            for item in node.values():
                _depth(item, level + 1)
        elif isinstance(node, list):
            for item in node:
                _depth(item, level + 1)

    _depth(spec, 0)


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
    # visible / hidden may carry an "@alias" string resolved via
    # DCC["STUDIO_CALLABLES"]; every other code-only key stays banned.
    from .callables import ALIASABLE_KEYS, is_alias

    aliased = {k for k in ALIASABLE_KEYS if is_alias(config.get(k))}
    unsafe = _UNSAFE_KEYS.intersection(config) - aliased
    if unsafe:
        raise ValidationError(f"{where}.{type_name}: {sorted(unsafe)} take code, not configuration")
    jsonable_config = {k: v for k, v in config.items() if k not in aliased}
    _check_jsonable(jsonable_config, f"{where}.{type_name}.config")

    if aliased:
        from .callables import resolve_config_aliases

        config = resolve_config_aliases(config)

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


def build_widgets_from_spec(nodes: list[dict[str, Any]]) -> list[Any]:
    from ..panels import WIDGET_TYPES

    return [_instantiate(WIDGET_TYPES, node, f"widgets[{i}]") for i, node in enumerate(nodes or [])]


def validate_widgets_spec(nodes: Any) -> None:
    """Raise ``ValidationError`` if any widget node is malformed. Called from
    ``PanelDashboard.clean``."""
    if not isinstance(nodes, list):
        raise ValidationError("widgets: expected a list of widget nodes")
    from ..panels import WIDGET_TYPES

    for i, node in enumerate(nodes):
        _instantiate(WIDGET_TYPES, node, f"widgets[{i}]")
        query = (node.get("config") or {}).get("query") if isinstance(node, dict) else None
        if query is not None:
            _check_query_shape(query, f"widgets[{i}].query")


# -- constrained aggregation for widget .query({...}) -----------------

_AGGREGATES = frozenset({"count", "sum", "avg", "min", "max"})


def _model_from_label(label: str, where: str) -> Any:
    from django.apps import apps

    from ..conf import dcc_settings

    if label not in set(dcc_settings.STUDIO_MODELS):
        raise ValidationError(f"{where}: model {label!r} is not listed in DCC['STUDIO_MODELS']")
    try:
        return apps.get_model(label)
    except (ValueError, LookupError) as exc:
        raise ValidationError(f"{where}: cannot resolve model {label!r}: {exc}") from None


def _require_field(model: Any, name: str, where: str) -> None:
    try:
        model._meta.get_field(name)
    except FieldDoesNotExist:
        raise ValidationError(f"{where}: {model.__name__} has no field {name!r}") from None


def _check_query_shape(spec: Any, where: str = "query") -> Any:
    if not isinstance(spec, dict):
        raise ValidationError(f"{where}: expected an object")
    model = _model_from_label(str(spec.get("model", "")), where)
    aggregate = spec.get("aggregate", "count")
    if aggregate not in _AGGREGATES:
        raise ValidationError(f"{where}: aggregate must be one of {sorted(_AGGREGATES)}")
    if aggregate != "count":
        field = spec.get("aggregate_field")
        if not field:
            raise ValidationError(f"{where}: {aggregate} needs 'aggregate_field'")
        _require_field(model, str(field), where)
    return model


def resolve_series_query(spec: dict[str, Any]) -> list[tuple[Any, Any]]:
    """``{model, group_by, aggregate, aggregate_field?, limit?}`` -> ``[(label, value)]``."""
    from django.db.models import Avg, Count, Max, Min, Sum

    model = _check_query_shape(spec)
    group_by = str(spec.get("group_by", ""))
    _require_field(model, group_by, "query")
    aggregate = spec.get("aggregate", "count")
    funcs = {"count": Count, "sum": Sum, "avg": Avg, "min": Min, "max": Max}
    expr = Count("pk") if aggregate == "count" else funcs[aggregate](str(spec["aggregate_field"]))
    limit = int(spec.get("limit", 50))
    rows = model._default_manager.values(group_by).annotate(_value=expr).order_by(group_by)[:limit]
    return [(row[group_by], row["_value"]) for row in rows]


def resolve_stat_query(spec: dict[str, Any]) -> Any:
    """Like :func:`resolve_series_query` but no ``group_by`` — a single scalar."""
    from django.db.models import Avg, Max, Min, Sum

    model = _check_query_shape(spec)
    aggregate = spec.get("aggregate", "count")
    if aggregate == "count":
        return model._default_manager.count()
    funcs = {"sum": Sum, "avg": Avg, "min": Min, "max": Max}
    field = str(spec["aggregate_field"])
    result = model._default_manager.aggregate(_value=funcs[aggregate](field))
    return result["_value"]


def validate_spec(spec: dict[str, Any], *, model: Any = None, request: Any = None) -> None:
    """Raise ``ValidationError`` if any table/infolist node is malformed.

    Called from ``DashboardSpec.clean``. When ``model`` is given every ORM path
    the spec names (column / entry ``name``, ``sortable`` / ``searchable``,
    filter ``field``, schema layout leaf names) is checked against
    ``studio.introspect.safe_paths`` so a spec can never reach
    ``author__user__password``; a schema ``fields: "__all__"`` is also rejected.
    """
    from ..infolists import ENTRY_TYPES
    from ..tables import COLUMN_TYPES, FILTER_TYPES

    _check_size_and_depth(spec)
    for i, node in enumerate((spec.get("table") or {}).get("columns", [])):
        _instantiate(COLUMN_TYPES, node, f"table.columns[{i}]")
    for i, node in enumerate((spec.get("table") or {}).get("filters", [])):
        _instantiate(FILTER_TYPES, node, f"table.filters[{i}]")
    for i, node in enumerate((spec.get("infolist") or {}).get("entries", [])):
        _instantiate(ENTRY_TYPES, node, f"infolist.entries[{i}]")

    if model is not None:
        _validate_spec_paths(spec, model, request)


def _validate_spec_paths(spec: dict[str, Any], model: Any, request: Any) -> None:
    from .introspect import normalize_path, safe_paths

    allowed = safe_paths(model, request)

    def check(path: Any, where: str) -> None:
        if not isinstance(path, str):
            return
        if normalize_path(path) not in allowed:
            raise ValidationError(f"{where}: {path!r} is not an allowed field of {model.__name__}")

    table = spec.get("table") or {}
    for i, node in enumerate(table.get("columns", [])):
        check(node.get("name"), f"table.columns[{i}].name")
        cfg = node.get("config") or {}
        if isinstance(cfg.get("sortable"), str):
            check(cfg["sortable"], f"table.columns[{i}].sortable")
        searchable = cfg.get("searchable")
        if isinstance(searchable, list):
            for j, field in enumerate(searchable):
                check(field, f"table.columns[{i}].searchable[{j}]")
    for i, node in enumerate(table.get("filters", [])):
        cfg = node.get("config") or {}
        check(cfg.get("field") or node.get("name"), f"table.filters[{i}].field")

    infolist = spec.get("infolist") or {}
    for i, node in enumerate(infolist.get("entries", [])):
        check(node.get("name"), f"infolist.entries[{i}].name")

    schema = spec.get("schema") or {}
    if schema.get("fields") == "__all__":
        raise ValidationError("schema.fields: '__all__' is not allowed in a stored spec")

    def walk_layout(nodes: Any, where: str) -> None:
        for i, node in enumerate(nodes or []):
            children = node.get("children") if isinstance(node, dict) else None
            if children:
                walk_layout(children, f"{where}[{i}].children")
            elif isinstance(node, dict) and node.get("name"):
                check(node["name"], f"{where}[{i}].name")

    walk_layout(schema.get("layout") or schema.get("components"), "schema.layout")
