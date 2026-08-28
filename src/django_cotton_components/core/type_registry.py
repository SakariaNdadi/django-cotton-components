"""String-keyed registries of the declarative building blocks.

Stored dashboard specs reference component types by name (``"TextColumn"``),
never by import path — the same posture as the action registry. A spec can only
name a type someone deliberately registered.
"""

from __future__ import annotations


class TypeRegistry[T]:
    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._types: dict[str, type[T]] = {}

    def register(self, cls: type[T], name: str | None = None) -> type[T]:
        self._types[name or cls.__name__] = cls
        return cls

    def get(self, name: str) -> type[T]:
        try:
            return self._types[name]
        except KeyError:
            raise KeyError(
                f"Unknown {self._kind} type {name!r}. Registered: {sorted(self._types)}"
            ) from None

    def names(self) -> list[str]:
        return sorted(self._types)

    def __contains__(self, name: str) -> bool:
        return name in self._types
