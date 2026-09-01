"""Reusable fluent-setter mixins.

Each mixin adds hand-written setters (annotated ``-> Self``) that stash into
``_config``. Field and layout components compose these.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from .component import UNSET, setter

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


class HasVisibilityRules:
    """Compiles ``.visible_when(...)`` calls into a client-side Alpine expression
    (``_visible_expr()``) evaluated live against sibling form values, via
    ``$dccField`` — see ``core/visibility.py``. Shared by ``Field`` and
    ``Layout``: a whole section can react to another field exactly like a
    single field can."""

    _config: dict[str, Any]
    _set: Callable[[str, Any], Self]

    def visible_when(self, field: str, *, equals: Any = UNSET, is_in: Any = UNSET) -> Self:
        from .visibility import VisibilityRule

        rule = VisibilityRule(
            field=field,
            equals=None if equals is UNSET else equals,
            is_in=None if is_in is UNSET else tuple(is_in),
            truthy=equals is UNSET and is_in is UNSET,
        )
        rules = [*self._config.get("visibility_rules", []), rule]
        return self._set("visibility_rules", rules)

    def _visible_expr(self) -> str:
        from .visibility import VisibilityRule

        rules: list[VisibilityRule] = self._config.get("visibility_rules", [])
        if not rules:
            return ""
        return " && ".join(f"({r.to_alpine()})" for r in rules)


class HasChildComponents:
    _children: list[Any]

    def schema(self, components: list[Any]) -> Self:
        self._children = list(components)
        return self

    components = schema
