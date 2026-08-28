from ..core.type_registry import TypeRegistry
from .columns import (
    BadgeColumn,
    BooleanColumn,
    Column,
    DateColumn,
    ImageColumn,
    TextColumn,
)
from .filters import BooleanFilter, Filter, SelectFilter, TernaryFilter
from .table import Table

COLUMN_TYPES: TypeRegistry[Column] = TypeRegistry("column")
FILTER_TYPES: TypeRegistry[Filter] = TypeRegistry("filter")
for _c in (TextColumn, BadgeColumn, BooleanColumn, DateColumn, ImageColumn):
    COLUMN_TYPES.register(_c)
for _f in (Filter, SelectFilter, BooleanFilter, TernaryFilter):
    FILTER_TYPES.register(_f)

__all__ = [
    "COLUMN_TYPES",
    "FILTER_TYPES",
    "BadgeColumn",
    "BooleanColumn",
    "BooleanFilter",
    "Column",
    "DateColumn",
    "Filter",
    "ImageColumn",
    "SelectFilter",
    "Table",
    "TernaryFilter",
    "TextColumn",
]
