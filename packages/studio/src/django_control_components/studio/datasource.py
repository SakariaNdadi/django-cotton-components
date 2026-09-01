"""A ``DataSource`` — the widget ``.query({...})`` DSL generalised into a prop
any block or widget can carry to pull rows from a model, server-side only.

    {"model": "shop.Order", "fields": ["id", "total", "customer__name"],
     "filter": {"status": "open"}, "order_by": ["-created_at"], "limit": 25}

Every path is checked against ``introspect.safe_paths(model, request, depth=1)``
— the same allowlist ``_validate_spec_paths`` enforces — and the model must be
listed in ``DCC["STUDIO_MODELS"]``. No ORM key ever comes from a request:
``tables/query.py``'s rule holds here too.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.core.exceptions import ValidationError

from .deserialize import _model_from_label
from .introspect import normalize_path, safe_paths

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 25

#: field-lookup suffixes a filter key may append to an allowed path
_LOOKUPS = frozenset(
    {
        "exact",
        "iexact",
        "contains",
        "icontains",
        "in",
        "gt",
        "gte",
        "lt",
        "lte",
        "startswith",
        "istartswith",
        "endswith",
        "iendswith",
        "range",
        "date",
        "year",
        "month",
        "day",
        "isnull",
        "regex",
        "iregex",
    }
)


def _base_path(key: str) -> str:
    parts = normalize_path(str(key)).split("__")
    if len(parts) > 1 and parts[-1] in _LOOKUPS:
        parts = parts[:-1]
    return "__".join(parts)


def validate_data_source(spec: Any, request: Any = None, *, where: str = "data_source") -> Any:
    """Raise ``ValidationError`` unless ``spec`` is a resolvable data source.
    Returns the resolved model class."""
    if not isinstance(spec, dict):
        raise ValidationError(f"{where}: expected an object")
    model = _model_from_label(str(spec.get("model", "")), where)
    allowed = safe_paths(model, request, depth=1)

    for field in spec.get("fields") or []:
        if normalize_path(str(field)) not in allowed:
            raise ValidationError(
                f"{where}.fields: {field!r} is not an allowed path of {model.__name__}"
            )
    for key in spec.get("filter") or {}:
        if _base_path(key) not in allowed:
            raise ValidationError(
                f"{where}.filter: {key!r} is not an allowed path of {model.__name__}"
            )
    for term in spec.get("order_by") or []:
        if normalize_path(str(term).lstrip("-")) not in allowed:
            raise ValidationError(
                f"{where}.order_by: {term!r} is not an allowed path of {model.__name__}"
            )
    limit = spec.get("limit", _DEFAULT_LIMIT)
    if not isinstance(limit, int) or limit < 1:
        raise ValidationError(f"{where}.limit: expected a positive integer")
    return model


def resolve_queryset(spec: dict[str, Any], request: Any = None) -> Any:
    """The (already sliced, already ordered) queryset for a validated source."""
    validate_data_source(spec, request)
    model = apps.get_model(str(spec["model"]))
    queryset = model._default_manager.all()
    filters = spec.get("filter") or {}
    if filters:
        queryset = queryset.filter(**{str(k): v for k, v in filters.items()})
    order_by = [str(term) for term in spec.get("order_by") or []]
    if order_by:
        queryset = queryset.order_by(*order_by)
    limit = min(int(spec.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    return queryset[:limit]


def resolve_table(spec: dict[str, Any], request: Any = None) -> Any:
    """A :class:`~django_control_components.tables.Table` over the source, with a
    text column per named field (or every own field when ``fields`` is omitted)."""
    from .deserialize import build_table_from_spec

    model = validate_data_source(spec, request)
    queryset = resolve_queryset(spec, request)
    fields = [str(f) for f in spec.get("fields") or []] or [
        f.name for f in model._meta.get_fields() if getattr(f, "concrete", False)
    ]
    column_spec = {"columns": [{"type": "TextColumn", "name": name} for name in fields]}
    return build_table_from_spec(queryset, column_spec)
