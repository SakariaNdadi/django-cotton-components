"""Table filters.

Each filter validates its incoming querystring value through a Django form
field. Anything that does not clean is ignored (the filter is simply not
applied) rather than raising - a garbage ``?f_status=`` must not 500 the page.
"""

from __future__ import annotations

from typing import Any, Self

from django import forms
from django.db.models import Q, QuerySet

from ..core.component import setter


class Filter:
    form_field: forms.Field = forms.CharField(required=False)

    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self._config: dict[str, Any] = {}
        for key, value in kwargs.items():
            method = getattr(type(self), key, None)
            if method is None or not getattr(method, "__dcc_setter__", False):
                raise TypeError(f"{type(self).__name__} has no setter {key!r}")
            getattr(self, key)(value)

    @classmethod
    def make(cls, name: str, **kwargs: Any) -> Self:
        return cls(name, **kwargs)

    @setter
    def label(self, value: str) -> Self:
        self._config["label"] = value
        return self

    @setter
    def field(self, value: str) -> Self:
        self._config["orm_field"] = value
        return self

    @property
    def header(self) -> str:
        return self._config.get("label", self.name.replace("_", " ").title())

    @property
    def orm_field(self) -> str:
        return self._config.get("orm_field", self.name)

    def clean(self, raw: str | None) -> Any:
        try:
            return self.form_field.clean(raw)
        except forms.ValidationError:
            return None

    def apply(self, queryset: QuerySet[Any], raw: str | None) -> QuerySet[Any]:
        value = self.clean(raw)
        if value in (None, "", []):
            return queryset
        return queryset.filter(Q(**{self.orm_field: value}))

    def choices(self) -> list[tuple[str, str]]:
        return []


class SelectFilter(Filter):
    def __init__(self, name: str, **kwargs: Any) -> None:
        super().__init__(name, **kwargs)
        self.form_field = forms.CharField(required=False)

    @setter
    def options(self, value: Any) -> Self:
        pairs = value.items() if isinstance(value, dict) else value
        self._config["options"] = [(str(v), str(label)) for v, label in pairs]
        return self

    def choices(self) -> list[tuple[str, str]]:
        return [("", "All"), *self._config.get("options", [])]

    def clean(self, raw: str | None) -> Any:
        allowed = {v for v, _ in self._config.get("options", [])}
        return raw if raw in allowed else None


class BooleanFilter(Filter):
    def clean(self, raw: str | None) -> Any:
        if raw == "true":
            return True
        if raw == "false":
            return False
        return None

    def choices(self) -> list[tuple[str, str]]:
        return [("", "All"), ("true", "Yes"), ("false", "No")]


class TernaryFilter(BooleanFilter):
    pass
