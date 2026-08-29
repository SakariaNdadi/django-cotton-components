# No-code resources (studio)

`django_control_components.studio` lets an admin define a panel resource from
**stored JSON** instead of a Python subclass — the seam a visual dashboard
builder would sit on top of. The builder UI itself is not included yet.

## Enable it

Studio ships as a **separate distribution** (`django-control-components-studio`).
Install it via the extra:

```bash
pip install "django-control-components[studio]"
```

```python
INSTALLED_APPS = [
    # ...
    "django_control_components",
    "django_control_components.studio",
]
```

Calling `.studio()` or `.dynamic()` on a `Panel` without the extra installed
raises `ImproperlyConfigured` with the install hint.

```python
admin_panel = Panel("admin").path("panel").resources([...]).dynamic()
```

`.dynamic()` adds `d/<slug>/…` routes that resolve a `DashboardSpec` row per
request, plus its entries to `panel.navigation()`.

## The spec

`DashboardSpec` has `slug`, `model` (`"app_label.ModelName"`), and three JSON
fields: `table`, `schema`, `infolist`. Each is a tree of
`{"type": "...", "name": "...", "config": {...}, "children": [...]}` nodes.

```python
DashboardSpec.objects.create(
    slug="comments",
    label="Comments",
    model="demo.Comment",
    table={
        "columns": [
            {"type": "TextColumn", "name": "author_name", "config": {"sortable": True}},
            {"type": "BooleanColumn", "name": "approved", "config": {"labels": ["✓", "—"]}},
        ],
        "filters": [{"type": "TernaryFilter", "name": "approved"}],
        "default_sort": "author_name",
    },
    schema={
        "fields": ["article", "author_name", "body", "approved"],
        "layout": [
            {"type": "TextInput", "name": "author_name", "config": {"required": True}},
            {"type": "Textarea", "name": "body"},
            {"type": "Toggle", "name": "approved"},
        ],
    },
    infolist={"entries": [
        {"type": "TextEntry", "name": "author_name"},
        {"type": "BooleanEntry", "name": "approved"},
    ]},
)
```

`config` values are passed straight to the builder's fluent setters
(`{"sortable": true}` → `.sortable(True)`), validated against the same
`@setter` whitelist the fluent API uses.

## What a spec cannot do

- **Name a type that isn't registered** — only `COLUMN_TYPES` / `FILTER_TYPES` /
  `FIELD_TYPES` / `ENTRY_TYPES` members. No import paths.
- **Carry a callable** — `config` must be JSON (`str`/`int`/`float`/`bool`/`null`/
  `list`/`dict`). Setters that take code (`state`, `action`, `authorize`,
  `visible`, `hidden`) are rejected outright.
- **Invent a model** — `model` must resolve via `apps.get_model`. Studio configures
  views over *existing* models; it does not create migrations.

Specs are validated in `DashboardSpec.clean()` (called from `save()`), so a bad
spec never reaches the request path. Row-level access still goes through
`Resource.get_queryset` / `can()` and the panel's `.auth()` guards; the client
only ever sends the spec slug, never a type name.

## Attaching code to a config-defined resource

Custom logic (a computed column, an action callback) stays in Python: subclass
`DynamicResource`, call `super().build_table(...)`, and add to the returned
builder before returning it.
