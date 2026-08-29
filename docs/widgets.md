# Widgets

Widgets are the blocks on a panel dashboard. Each one renders a persistent shell
(`<div class="dcc-widget" id="…">`) around a swappable content fragment
(`#<id>-content`). `.poll()` / `.refresh_on()` make the shell re-fetch just that
fragment over htmx, so a chart repaints without a full page load.

Compose them in `DashboardPage.widgets(request)`:

```python
from django_control_components.panels import (
    BarListWidget, ChartWidget, DashboardPage, StatWidget, TableWidget,
)

class Overview(DashboardPage):
    page_title = "Overview"

    def widgets(self, request):
        return [
            StatWidget.make("Articles", Article.objects.count()).icon("newspaper"),
            StatWidget.make("Open comments", lambda r: Comment.objects.filter(approved=False).count())
                .icon("comments").poll(30),
            ChartWidget.make("Articles over time").kind("area").data(_by_month).columns(2),
            BarListWidget.make("By status").data([("Live", 8), ("Draft", 3)]),
            TableWidget.make("Recent", _recent_table),
        ]
```

## Shared API

Every widget:

| method | effect |
| --- | --- |
| `.make(*args, **kwargs)` | construct; keyword args are applied as setters |
| `.id(str)` | stable id — the `?_dcc_widget=<id>` refresh handle and json_script id. Auto-assigned `w0`, `w1`, … when unset |
| `.columns(n)` | grid span (stat 1, chart/bar-list 2, table 3 by default) |
| `.poll(seconds)` | re-fetch the content fragment on an interval |
| `.refresh_on(event="dcc:refresh")` | re-fetch when a page event fires. `ChartWidget` and `StatWidget` do this by default, so a table/resource mutation (which fires `dcc:refresh`) repaints them |

## `StatWidget`

`StatWidget.make(label, value=None)` — `.value(x | callable)`, `.description(text)`,
`.icon(name)`, `.query({...})`. A callable value may take `request`.

## `ChartWidget` — Chart.js

`ChartWidget.make(label)`:

- `.kind("line" | "bar" | "area" | "pie" | "doughnut" | "radar")` — `area` is a
  filled line.
- `.data(pairs | {labels, datasets} | callable)` — a `(label, value)` list becomes
  one dataset; a Chart.js `{labels, datasets}` dict passes straight through.
- `.options(dict)` — merged over `{responsive: true, maintainAspectRatio: false}`.
- `.query({...})` — the no-code data path (below).

Chart.js loads from the CDN, on demand, only on dashboards that use a chart — the
`DashboardPage` collects each widget's `assets` and emits them once in the page
`<head>`. Nothing is added to `{% dcc_assets %}`.

## `BarListWidget`

`BarListWidget.make(label).data([(label, value), …])` — a dependency-free CSS bar
chart. No JavaScript, no CDN. Good for a compact breakdown where a full charting
library is overkill.

## `TableWidget`

`TableWidget.make(label, table)` — `table` is a `Table` or `table(request)`. The
table keeps its own toolbar, pagination and refresh.

## Writing a custom widget

A widget is a Python class + a content template. Override `context(request)` for
plain server-rendered markup, or `payload(request)` to hand a JSON blob to an
Alpine component.

```python
from django_control_components.panels import Widget
from django_control_components.panels.assets import Asset

class SparklineWidget(Widget):
    template_name = "myapp/widgets/sparkline.html"
    variant = "sparkline"                 # -> class="dcc-widget--sparkline"
    js_component = "mySparkline"          # Alpine.data() name, optional
    assets = (Asset("script", "https://cdn.jsdelivr.net/npm/…"),)
    auto_refresh = True

    def __init__(self, label, **kwargs):
        super().__init__(**kwargs)
        self._config["label"] = label

    def payload(self, request):
        return {"points": list(self._series(request))}
```

```django
{# myapp/widgets/sparkline.html — the content fragment only, no outer .dcc-widget #}
<div class="dcc-widget__label">{{ label }}</div>
<div x-data="mySparkline('{{ payload_id }}')">
  {{ payload|json_script:payload_id }}
  <svg x-ref="chart"></svg>
</div>
```

The `x-data` must be a single factory call taking the `payload_id` string — no
other `{{ }}` inside `x-data` (a template-linting test enforces this).

## Registering a charting library

`ChartWidget` delegates drawing to a renderer keyed by `payload.library`
(`"chartjs"` is built in). Add another library from your own `<script>`:

```html
<script>
  window.dccWidgets.register("apexcharts", function (node, payload) {
    var chart = new ApexCharts(node, payload.options);
    chart.render();
    return chart;                 // returning something with .destroy() is enough
  });
</script>
```

Then a widget whose `payload()` returns `{"library": "apexcharts", …}` renders
through it. The returned object's `.destroy()` is called before every re-draw and
on teardown, so an htmx fragment swap does not leak the canvas/DOM.

## No-code: `.query({...})`

`ChartWidget.query()` and `StatWidget.query()` take a constrained aggregation spec
resolved server-side — the only chart data path expressible in a stored
`PanelDashboard` JSON row:

```json
{"model": "blog.Article", "group_by": "status", "aggregate": "count"}
{"model": "blog.Article", "aggregate": "sum", "aggregate_field": "views"}
```

- `model` **must** be listed in `DCC["STUDIO_MODELS"]` — a spec cannot aggregate an
  arbitrary table.
- `aggregate` ∈ `{count, sum, avg, min, max}`; anything but `count` needs
  `aggregate_field`.
- `group_by` / `aggregate_field` are validated against the model's fields.
- `limit` (default 50) caps the number of groups.

A stored dashboard:

```python
PanelDashboard.objects.create(
    slug="metrics", label="Metrics",
    widgets=[
        {"type": "StatWidget", "name": "Articles",
         "config": {"query": {"model": "blog.Article", "aggregate": "count"}}},
        {"type": "ChartWidget", "name": "By status",
         "config": {"kind": "doughnut",
                    "query": {"model": "blog.Article", "group_by": "status",
                              "aggregate": "count"}}},
    ],
)
```

`Panel(...).dynamic()` serves it at `<panel>/dash/<slug>/` and lists it in the
sidebar. As with resource specs, the client only ever sends the dashboard slug —
never a model label or a type name.
