"""Dashboard widgets - self-contained blocks for a panel's index page.

Every widget renders a persistent shell (``<div class="dcc-widget" id="...">``)
around a swappable content fragment (``#<id>-content``). ``.poll(seconds)`` and
``.refresh_on(event)`` make the shell re-fetch just that fragment over htmx, so a
chart repaints without a full page load.

``ChartWidget`` draws with Chart.js (loaded on demand via :class:`Asset`);
``BarListWidget`` is a dependency-free CSS bar chart. A third-party library is
added by registering a renderer in ``window.dccWidgets`` - see ``dcc.js``.
"""

from __future__ import annotations

import inspect
from typing import Any, ClassVar, Self

from django.template.loader import render_to_string
from django.utils.safestring import SafeString

from .. import htmx as htmx_adapter
from ..core.component import setter
from ..icons import render_icon
from .assets import CHARTJS_SRC, Asset


def _wants_request(fn: Any) -> bool:
    try:
        return "request" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def _resolve(value: Any, request: Any) -> Any:
    if callable(value):
        return value(request) if _wants_request(value) else value()
    return value


class Widget:
    template_name: ClassVar[str] = ""  # the content fragment template
    shell_template: ClassVar[str] = "django_control_components/panels/widgets/_shell.html"
    variant: ClassVar[str] = "widget"  # -> class="dcc-widget--<variant>"
    span: ClassVar[int] = 1  # grid columns
    js_component: ClassVar[str] = ""  # Alpine.data() name mounted on the content
    assets: ClassVar[tuple[Asset, ...]] = ()
    auto_refresh: ClassVar[bool] = False  # repaint on the page-wide dcc:refresh event

    def __init__(self, **kwargs: Any) -> None:
        self._config: dict[str, Any] = {}
        self._auto_id: str | None = None
        self._apply_kwargs(kwargs)

    @classmethod
    def make(cls, *args: Any, **kwargs: Any) -> Self:
        return cls(*args, **kwargs)

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

    # -- shared setters -------------------------------------------------

    @setter
    def id(self, value: str) -> Self:
        return self._set("id", value)

    @setter
    def columns(self, n: int) -> Self:
        return self._set("span", n)

    @setter
    def poll(self, seconds: int) -> Self:
        return self._set("poll", int(seconds))

    @setter
    def refresh_on(self, event: str = "dcc:refresh") -> Self:
        self._config.setdefault("refresh_events", []).append(event)
        return self

    # -- identity ----------------------------------------------------

    def get_id(self) -> str:
        explicit = self._config.get("id")
        if explicit:
            return str(explicit)
        if self._auto_id is None:
            self._auto_id = "w" + format(id(self) % 0x1000000, "x")
        return self._auto_id

    def get_span(self) -> int:
        return int(self._config.get("span", self.span))

    def get_assets(self) -> tuple[Asset, ...]:
        return self.assets

    # -- content hooks (override) ----------------------------------

    def context(self, request: Any) -> dict[str, Any]:
        return {}

    def payload(self, request: Any) -> dict[str, Any] | None:
        """JSON-serialisable data rendered into a ``json_script`` blob for the
        widget's Alpine component. ``None`` = no blob."""
        return None

    # -- rendering -------------------------------------------------

    def _content_data(self, request: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            "span": self.get_span(),
            "widget_id": self.get_id(),
            "js_component": self.js_component,
            **self.context(request),
        }
        payload = self.payload(request)
        if payload is not None:
            data["payload"] = payload
            data["payload_id"] = f"{self.get_id()}-data"
        return data

    def render_content(self, request: Any = None) -> SafeString:
        return SafeString(
            render_to_string(self.template_name, self._content_data(request), request=request)
        )

    def _refresh_triggers(self) -> list[str]:
        triggers: list[str] = []
        if self._config.get("poll"):
            triggers.append(f"every {self._config['poll']}s")
        events = self._config.get("refresh_events")
        if events is None and self.auto_refresh:
            events = ["dcc:refresh"]
        triggers.extend(f"{event} from:body" for event in events or [])
        return triggers

    def _shell_htmx(self, request: Any) -> Any:
        triggers = self._refresh_triggers()
        if not triggers:
            return None
        path = getattr(request, "path", "") or ""
        return htmx_adapter.get(
            f"{path}?_dcc_widget={self.get_id()}",
            target=f"#{self.get_id()}-content",
            swap="innerHTML",
            trigger=", ".join(triggers),
        )

    def render(self, request: Any = None) -> SafeString:
        data = {
            "widget_id": self.get_id(),
            "variant": self.variant,
            "span": self.get_span(),
            "shell_htmx": self._shell_htmx(request),
            "content_html": self.render_content(request),
        }
        return SafeString(render_to_string(self.shell_template, data, request=request))


class StatWidget(Widget):
    template_name = "django_control_components/panels/widgets/stat.html"
    variant = "stat"
    auto_refresh = True

    def __init__(self, label: str, value: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._config["label"] = label
        self._config["value"] = value

    @setter
    def value(self, value: Any) -> Self:
        return self._set("value", value)

    @setter
    def description(self, text: str) -> Self:
        return self._set("description", text)

    @setter
    def icon(self, name: str) -> Self:
        return self._set("icon", name)

    @setter
    def query(self, spec: dict[str, Any]) -> Self:
        return self._set("query", spec)

    def context(self, request: Any) -> dict[str, Any]:
        value = self._config.get("value")
        if value is None and self._config.get("query"):
            from ._studio import require_studio

            value = require_studio("deserialize").resolve_stat_query(self._config["query"])
        else:
            value = _resolve(value, request)
        return {
            "label": self._config["label"],
            "value": value,
            "description": self._config.get("description", ""),
            "icon_html": render_icon(self._config.get("icon")),
        }


class ChartWidget(Widget):
    """A Chart.js chart. ``.data([(label, value), ...])`` or a ``{labels, datasets}``
    dict or a callable; ``.query({...})`` for the no-code aggregation path."""

    template_name = "django_control_components/panels/widgets/chart.html"
    variant = "chart"
    span = 2
    js_component = "dccChart"
    assets = (Asset("script", CHARTJS_SRC),)
    auto_refresh = True

    _KINDS = frozenset({"line", "bar", "area", "pie", "doughnut", "radar"})

    def __init__(self, label: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._config["label"] = label

    @setter
    def kind(self, value: str) -> Self:
        if value not in self._KINDS:
            raise ValueError(f"ChartWidget.kind must be one of {sorted(self._KINDS)}")
        return self._set("kind", value)

    @setter
    def data(self, value: Any) -> Self:
        return self._set("data", value)

    @setter
    def options(self, value: dict[str, Any]) -> Self:
        return self._set("options", value)

    @setter
    def query(self, spec: dict[str, Any]) -> Self:
        return self._set("query", spec)

    def _dataset_shape(self, request: Any) -> dict[str, Any]:
        raw = self._config.get("data")
        if raw is None and self._config.get("query"):
            from ._studio import require_studio

            raw = require_studio("deserialize").resolve_series_query(self._config["query"])
        raw = _resolve(raw, request)
        if isinstance(raw, dict):
            return raw
        pairs = list(raw or [])
        return {
            "labels": [str(label) for label, _ in pairs],
            "datasets": [{"label": self._config.get("label") or "", "data": [v for _, v in pairs]}],
        }

    def payload(self, request: Any) -> dict[str, Any]:
        kind = self._config.get("kind", "bar")
        data = self._dataset_shape(request)
        if kind == "area":
            for dataset in data.get("datasets", []):
                dataset.setdefault("fill", True)
        options = {
            "responsive": True,
            "maintainAspectRatio": False,
            **self._config.get("options", {}),
        }
        return {
            "library": "chartjs",
            "type": "line" if kind == "area" else kind,
            "data": data,
            "options": options,
        }

    def context(self, request: Any) -> dict[str, Any]:
        return {"label": self._config["label"]}


class BarListWidget(Widget):
    """A dependency-free CSS bar chart - ``.data([(label, value), ...])``."""

    template_name = "django_control_components/panels/widgets/bar_list.html"
    variant = "bar-list"
    span = 2

    def __init__(self, label: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._config["label"] = label

    @setter
    def data(self, value: Any) -> Self:
        return self._set("data", value)

    def context(self, request: Any) -> dict[str, Any]:
        raw = _resolve(self._config.get("data"), request) or []
        pairs = list(raw)
        top = max((value for _, value in pairs), default=1) or 1
        bars = [
            {"label": label, "value": value, "pct": round(100 * value / top, 1)}
            for label, value in pairs
        ]
        return {"label": self._config["label"], "bars": bars}


class TableWidget(Widget):
    template_name = "django_control_components/panels/widgets/table.html"
    variant = "table"
    span = 3

    def __init__(self, label: str = "", table: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._config["label"] = label
        if table is not None:
            self._config["table"] = table

    @setter
    def table(self, value: Any) -> Self:
        return self._set("table", value)

    @setter
    def data_source(self, value: Any) -> Self:
        """A stored ``DataSource`` dict (``{model, fields, filter, order_by,
        limit}``). The studio turns it into a ``Table`` server-side before
        render; a code caller passes a ``Table`` to :meth:`table` instead."""
        return self._set("data_source", value)

    def context(self, request: Any) -> dict[str, Any]:
        table = self._config.get("table")
        table = table(request) if callable(table) else table
        html = table.render(request) if table is not None else ""
        return {"label": self._config["label"], "table_html": html}
