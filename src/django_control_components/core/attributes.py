from __future__ import annotations

from typing import Any

from django.utils.html import format_html_join
from django.utils.safestring import SafeString, mark_safe

_BOOLEAN_ATTRS = frozenset(
    {"required", "disabled", "checked", "readonly", "multiple", "selected", "autofocus", "hidden"}
)


class AttributeBag:
    """Accumulates HTML attributes and renders them safely.

    ``class`` is the only attribute that *merges* - appending a caller-supplied
    value to component defaults rather than replacing them. Everything else is
    last-write-wins. Values are escaped at render time; keys are validated.
    """

    __slots__ = ("_attrs", "_classes")

    def __init__(self, *sources: dict[str, Any] | None) -> None:
        self._attrs: dict[str, Any] = {}
        self._classes: list[str] = []
        for source in sources:
            if source:
                self.update(source)

    def update(self, source: dict[str, Any]) -> AttributeBag:
        for key, value in source.items():
            self.set(key, value)
        return self

    def set(self, key: str, value: Any) -> AttributeBag:
        key = key.strip()
        if not key or any(c.isspace() or c in "\"'>/=" for c in key):
            raise ValueError(f"Unsafe attribute name: {key!r}")
        if key == "class":
            self.add_class(value)
        elif value is not None and value is not False:
            self._attrs[key] = value
        return self

    def add_class(self, value: Any) -> AttributeBag:
        if not value:
            return self
        parts = value.split() if isinstance(value, str) else list(value)
        for part in parts:
            if part and part not in self._classes:
                self._classes.append(part)
        return self

    def as_dict(self) -> dict[str, Any]:
        out = dict(self._attrs)
        if self._classes:
            out["class"] = " ".join(self._classes)
        return out

    def render(self) -> SafeString:
        pairs: list[tuple[str, Any]] = []
        for key, value in self.as_dict().items():
            if key in _BOOLEAN_ATTRS:
                if value:
                    pairs.append((key, key))
                continue
            pairs.append((key, "" if value is True else str(value)))
        if not pairs:
            return mark_safe("")
        return format_html_join(" ", '{}="{}"', pairs)

    __str__ = render

    def __html__(self) -> SafeString:
        return self.render()
