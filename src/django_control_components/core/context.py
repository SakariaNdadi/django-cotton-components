from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.forms import BaseForm
    from django.http import HttpRequest

Operation = Literal["create", "edit", "view"]


@dataclass(frozen=True, slots=True)
class RenderContext:
    """Per-request state for one render pass.

    Components never hold request state on ``self``; it flows through here so a
    single component instance can be rendered concurrently against different
    requests without cross-talk.
    """

    request: HttpRequest | None = None
    record: Any | None = None
    form: BaseForm | None = None
    operation: Operation = "create"
    parent: Any | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def user(self) -> Any | None:
        return getattr(self.request, "user", None)

    def child(self, **overrides: Any) -> RenderContext:
        overrides.setdefault("parent", None)
        return replace(self, **overrides)

    def resolve(self, name: str) -> Any:
        """Look up an injectable name for closure evaluation."""
        if name == "context":
            return self
        if name == "get":
            return _StateReader(self.form)
        if name == "set":
            return _noop_setter
        if name == "state":
            return _StateReader(self.form)
        return getattr(self, name, None)


class _StateReader:
    """``get("field")`` -> current value of a sibling field on the bound form."""

    __slots__ = ("_form",)

    def __init__(self, form: BaseForm | None) -> None:
        self._form = form

    def __call__(self, name: str, default: Any = None) -> Any:
        if self._form is None:
            return default
        try:
            return self._form[name].value()
        except KeyError:
            return default


def _noop_setter(name: str, value: Any) -> None:
    # Server-render is one-shot; there is no live field state to write back.
    return
