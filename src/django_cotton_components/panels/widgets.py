"""Dashboard widgets — small self-contained blocks for a panel's index page.

Each widget renders server-side to a ``SafeString``; ``ChartWidget`` is a plain
CSS bar chart (no chart library, no Alpine). Compose them in
``DashboardPage.widgets(request)``.
"""

from __future__ import annotations

import inspect
from typing import Any, Self

from django.template.loader import render_to_string
from django.utils.safestring import SafeString

from ..icons import render_icon


def _wants_request(fn: Any) -> bool:
    try:
        return "request" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


class Widget:
    template_name = ""
    span = 1  # grid columns

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    @classmethod
    def make(cls, *args: Any, **kwargs: Any) -> Self:
        return cls(*args, **kwargs)

    def columns(self, n: int) -> Self:
        self._config["span"] = n
        return self

    def get_span(self) -> int:
        return int(self._config.get("span", self.span))

    def context(self, request: Any) -> dict[str, Any]:
        return {}

    def render(self, request: Any = None) -> SafeString:
        data = {"span": self.get_span(), **self.context(request)}
        return SafeString(render_to_string(self.template_name, data, request=request))


class StatWidget(Widget):
    template_name = "django_cotton_components/panels/widgets/stat.html"

    def __init__(self, label: str, value: Any = None) -> None:
        super().__init__()
        self._config["label"] = label
        self._config["value"] = value

    def value(self, value: Any) -> Self:
        self._config["value"] = value
        return self

    def description(self, text: str) -> Self:
        self._config["description"] = text
        return self

    def icon(self, name: str) -> Self:
        self._config["icon"] = name
        return self

    def context(self, request: Any) -> dict[str, Any]:
        value = self._config.get("value")
        if callable(value):
            value = value(request) if _wants_request(value) else value()
        return {
            "label": self._config["label"],
            "value": value,
            "description": self._config.get("description", ""),
            "icon_html": render_icon(self._config.get("icon")),
        }


class ChartWidget(Widget):
    template_name = "django_cotton_components/panels/widgets/chart.html"
    span = 2

    def __init__(self, label: str) -> None:
        super().__init__()
        self._config["label"] = label

    def data(self, pairs: Any) -> Self:
        self._config["data"] = pairs
        return self

    def context(self, request: Any) -> dict[str, Any]:
        raw = self._config.get("data") or []
        if callable(raw):
            raw = raw(request) if _wants_request(raw) else raw()
        pairs = list(raw)
        top = max((v for _, v in pairs), default=1) or 1
        bars = [
            {"label": label, "value": value, "pct": round(100 * value / top, 1)}
            for label, value in pairs
        ]
        return {"label": self._config["label"], "bars": bars}


class TableWidget(Widget):
    template_name = "django_cotton_components/panels/widgets/table.html"
    span = 3

    def __init__(self, label: str, table: Any) -> None:
        super().__init__()
        self._config["label"] = label
        self._config["table"] = table

    def context(self, request: Any) -> dict[str, Any]:
        table = self._config["table"]
        table = table(request) if callable(table) else table
        return {"label": self._config["label"], "table_html": table.render(request)}
