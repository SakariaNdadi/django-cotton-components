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

for _col_cls, _label, _icon in (
    (TextColumn, "Text", "font"),
    (BadgeColumn, "Badge", "tag"),
    (BooleanColumn, "Boolean", "check"),
    (DateColumn, "Date", "calendar"),
    (ImageColumn, "Image", "image"),
):
    COLUMN_TYPES.register(
        _col_cls,
        label=_label,
        icon=_icon,
        category="column",
        setters={"allow_html": {"requires": "superuser"}},
    )

for _filter_cls, _label, _icon in (
    (Filter, "Text filter", "filter"),
    (SelectFilter, "Select filter", "list"),
    (BooleanFilter, "Boolean filter", "check"),
    (TernaryFilter, "Yes / No / Any", "circle-half-stroke"),
):
    FILTER_TYPES.register(_filter_cls, label=_label, icon=_icon, category="filter")

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
