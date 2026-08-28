"""String-keyed registries of the declarative building blocks.

Stored dashboard specs reference component types by name (``"TextColumn"``),
never by import path — the same posture as the action registry. A spec can only
name a type someone deliberately registered.

Registration also carries the palette metadata (label, icon, category, whether
the type nests children, per-setter overrides) that the studio needs. Every
metadata argument is optional, so a bare ``register(cls)`` still works.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .describe import TypeInfo


class TypeRegistry[T]:
    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._types: dict[str, type[T]] = {}
        self._overrides: dict[str, dict[str, Any]] = {}

    def register(
        self,
        cls: type[T],
        name: str | None = None,
        *,
        label: str | None = None,
        icon: str = "",
        category: str = "",
        accepts_children: bool = False,
        help: str = "",
        setters: dict[str, dict[str, Any]] | None = None,
    ) -> type[T]:
        key = name or cls.__name__
        self._types[key] = cls
        overrides: dict[str, Any] = {}
        if label is not None:
            overrides["label"] = label
        if icon:
            overrides["icon"] = icon
        if category:
            overrides["category"] = category
        if accepts_children:
            overrides["accepts_children"] = True
        if help:
            overrides["help"] = help
        if setters:
            overrides["setters"] = setters
        self._overrides[key] = overrides
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

    def info(self, name: str) -> TypeInfo:
        from .describe import describe_type

        return describe_type(self.get(name), overrides=self._overrides.get(name))

    def describe_all(self) -> list[TypeInfo]:
        return [self.info(name) for name in self.names()]

    def __contains__(self, name: str) -> bool:
        return name in self._types
