from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, ClassVar, Self

from django.utils.safestring import SafeString

from .evaluate import evaluate

if TYPE_CHECKING:
    from collections.abc import Callable

    from .context import RenderContext


class Unset:
    """Sentinel distinct from ``None``.

    ``None`` is a legitimate configured value ("render no label"); ``UNSET``
    means "the caller said nothing, inherit the default / the Django field".
    """

    _instance: ClassVar[Unset | None] = None

    def __new__(cls) -> Unset:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET = Unset()


def setter(method: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method as a fluent setter usable as a constructor kwarg."""
    method.__dcc_setter__ = True  # type: ignore[attr-defined]
    return method


class Component:
    """Base fluent primitive.

    Subclasses declare ``template_name`` and hand-written setters (each returning
    ``Self``). Instances hold *configuration only* - never per-request state.
    """

    template_name: ClassVar[str] = ""

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self._name: str | None = name
        self._config: dict[str, Any] = {}
        self._children: list[Component] = []
        self._apply_kwargs(kwargs)

    # -- construction ----------------------------------------------------

    @classmethod
    def make(cls, name: str | None = None, **kwargs: Any) -> Self:
        return cls(name, **kwargs)

    def _apply_kwargs(self, kwargs: dict[str, Any]) -> None:
        for key, value in kwargs.items():
            method = getattr(type(self), key, None)
            if method is None or not getattr(method, "__dcc_setter__", False):
                valid = sorted(
                    n
                    for n in dir(type(self))
                    if getattr(getattr(type(self), n, None), "__dcc_setter__", False)
                )
                raise TypeError(f"{type(self).__name__} has no setter {key!r}. Valid: {valid}")
            getattr(self, key)(value)

    def _set(self, key: str, value: Any) -> Self:
        self._config[key] = value
        return self

    def _get(self, key: str, default: Any = UNSET) -> Any:
        return self._config.get(key, default)

    def clone(self) -> Self:
        new = copy.copy(self)
        new._config = copy.copy(self._config)
        new._children = [c.clone() for c in self._children]
        return new

    # -- identity ------------------------------------------------------

    @property
    def name(self) -> str | None:
        return self._name

    # -- shared setters ----------------------------------------------

    @setter
    def extra_attributes(self, attrs: dict[str, Any]) -> Self:
        merged = {**self._config.get("extra_attributes", {}), **attrs}
        return self._set("extra_attributes", merged)

    @setter
    def visible(self, value: bool | Callable[..., bool]) -> Self:
        return self._set("visible", value)

    @setter
    def hidden(self, value: bool | Callable[..., bool]) -> Self:
        return self._set("hidden", value)

    def when(self, condition: bool | Callable[..., bool]) -> Self:
        return self._set("visible", condition)

    def hidden_when(self, condition: bool | Callable[..., bool]) -> Self:
        return self._set("hidden", condition)

    # -- rendering ---------------------------------------------------

    def is_visible(self, ctx: RenderContext) -> bool:
        visible = self._config.get("visible", UNSET)
        if visible is not UNSET and not evaluate(visible, ctx, component=self):
            return False
        hidden = self._config.get("hidden", UNSET)
        return not (hidden is not UNSET and evaluate(hidden, ctx, component=self))

    def resolve(self, key: str, ctx: RenderContext, default: Any = UNSET) -> Any:
        return evaluate(self._config.get(key, default), ctx, component=self)

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        from .attributes import AttributeBag

        bag = AttributeBag(self._config.get("extra_attributes"))
        return {
            "name": self._name,
            "attrs": bag,
            "component": self,
        }

    def render(self, ctx: RenderContext) -> SafeString:
        from .renderer import render_component

        if not self.is_visible(ctx):
            return SafeString("")
        return render_component(self, ctx)
