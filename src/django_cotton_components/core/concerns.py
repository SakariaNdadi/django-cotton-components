"""Reusable fluent-setter mixins.

Each mixin adds hand-written setters (annotated ``-> Self``) that stash into
``_config``. Field and layout components compose these.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from .component import setter

if TYPE_CHECKING:
    from collections.abc import Callable


class HasLabel:
    _set: Callable[[str, Any], Self]

    @setter
    def label(self, value: str | Callable[..., str | None] | None) -> Self:
        return self._set("label", value)

    @setter
    def help_text(self, value: str | Callable[..., str | None] | None) -> Self:
        return self._set("help_text", value)

    @setter
    def placeholder(self, value: str | Callable[..., str]) -> Self:
        return self._set("placeholder", value)


class HasHint:
    _set: Callable[[str, Any], Self]

    @setter
    def hint(self, value: str | Callable[..., str]) -> Self:
        return self._set("hint", value)

    @setter
    def icon(self, value: str | Callable[..., str]) -> Self:
        return self._set("icon", value)


class HasState:
    _set: Callable[[str, Any], Self]

    @setter
    def required(self, value: bool | Callable[..., bool] = True) -> Self:
        return self._set("required", value)

    @setter
    def disabled(self, value: bool | Callable[..., bool] = True) -> Self:
        return self._set("disabled", value)

    @setter
    def readonly(self, value: bool | Callable[..., bool] = True) -> Self:
        return self._set("readonly", value)

    @setter
    def default(self, value: Any) -> Self:
        return self._set("default", value)


class HasColumnSpan:
    _set: Callable[[str, Any], Self]

    @setter
    def column_span(self, value: int | str) -> Self:
        return self._set("column_span", value)

    def column_span_full(self) -> Self:
        return self._set("column_span", "full")


class HasChildComponents:
    _children: list[Any]

    def schema(self, components: list[Any]) -> Self:
        self._children = list(components)
        return self

    components = schema
