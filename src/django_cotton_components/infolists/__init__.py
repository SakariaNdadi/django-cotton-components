from ..core.type_registry import TypeRegistry
from .entries import BadgeEntry, BooleanEntry, DateEntry, Entry, TextEntry
from .infolist import Infolist

ENTRY_TYPES: TypeRegistry[Entry] = TypeRegistry("entry")
for _entry_cls, _label, _icon in (
    (TextEntry, "Text", "font"),
    (BadgeEntry, "Badge", "tag"),
    (BooleanEntry, "Boolean", "check"),
    (DateEntry, "Date", "calendar"),
):
    ENTRY_TYPES.register(_entry_cls, label=_label, icon=_icon, category="entry")

__all__ = [
    "ENTRY_TYPES",
    "BadgeEntry",
    "BooleanEntry",
    "DateEntry",
    "Entry",
    "Infolist",
    "TextEntry",
]
