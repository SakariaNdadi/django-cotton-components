from ..core.type_registry import TypeRegistry
from .entries import BadgeEntry, BooleanEntry, DateEntry, Entry, TextEntry
from .infolist import Infolist

ENTRY_TYPES: TypeRegistry[Entry] = TypeRegistry("entry")
for _e in (TextEntry, BadgeEntry, BooleanEntry, DateEntry):
    ENTRY_TYPES.register(_e)

__all__ = [
    "ENTRY_TYPES",
    "BadgeEntry",
    "BooleanEntry",
    "DateEntry",
    "Entry",
    "Infolist",
    "TextEntry",
]
