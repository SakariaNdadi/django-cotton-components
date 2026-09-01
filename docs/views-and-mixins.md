# Views & mixins

Every view class and mixin the library ships, its MRO expectations, and which
methods to override vs. leave alone.

Two unrelated families share the word "mixin":

- **View mixins** (`mixins.py`, `tables/views.py`) — mix into your Django CBVs.
- **Concern mixins** (`core/concerns.py`) — compose into `Component` subclasses
  to add fluent setters. Covered last.

## View mixins

### `SchemaFormMixin` (`mixins.py`)

Drives a `FormView` / `CreateView` / `UpdateView` from a `Schema`.

```python
class ArticleUpdateView(SchemaFormMixin, UpdateView):
    model = Article
    template_name = "articles/form.html"

    def get_schema(self):
        return article_schema()
```

| aspect | detail |
|---|---|
| **MRO** | place **left** of the Django generic view. It calls `super().get_context_data()` and `super().form_valid()`, and reads `self.object` / `self.request`. |
| **class attr** | `schema: Schema \| None = None` |
| **override** | `get_schema(self) -> Schema` — build per request. Returning `None` raises `ValueError`. |
| provides | `get_form_class()` → `get_schema().get_form_class()` (do not also set `form_class`) |
| provides | `get_context_data()` adds `schema`, `schema_html` (rendered with the bound form + `self.object`) |
| provides | `form_valid()` → `super().form_valid()`, then `schema.process_images(self.object)` **iff** `self.object` is set and the schema has image specs |
| **do not override** | `form_valid` / `get_form_class` unless you reproduce the image step |

### `TableMixin` (`tables/views.py`)

Renders a `Table` and answers its htmx fragment requests.

```python
class ArticleListView(TableMixin, TemplateView):
    template_name = "articles/list.html"

    def get_table(self):
        return article_table(self.request)
```

| aspect | detail |
|---|---|
| **MRO** | place **before** the Django view (`TemplateView`, `ListView`) so `super().get()` / `super().get_context_data()` resolve to it. Place **auth mixins after** `TableMixin` — `dispatch` (auth) still runs first; the fragment is served from `get`, after `dispatch`. |
| **class attrs** | `table: Table \| None = None`, `table_context_name = "table_html"` |
| **override** | `get_table(self) -> Table`. Returning `None` raises `ValueError`. |
| provides | `get()` — on an `HX-Request` whose `?_dcc_table` matches the table id, returns `HttpResponse(table.render_content(request))`; else `super().get()` |
| provides | `get_context_data()` adds `{table_context_name: table.render(request)}` |
| **do not override** | `get()` unless you reproduce the fragment contract |

## Endpoint views

Both are mounted by `include("django_control_components.urls")` under your chosen
prefix. You do not subclass these.

### `ActionView` — `dcc:action` at `a/<owner_key>/<action_name>/`

`django.views.View`. `GET` renders the confirm / schema modal; `POST`
re-authorizes, re-scopes targets to the owner's queryset, validates the schema
form, runs the callback. Full behaviour and status codes: [actions.md](actions.md).

### `SchemaValidateView` — `dcc:schema-validate` at `v/<schema_key>/`

`django.views.View`, `POST` only. Behind `Field.live()`. Steps
(`schemas/endpoints.py`):

1. `_SCHEMAS.get(schema_key)` — unknown → `Http404("Unknown schema")`. Register
   with `register_schema(key, schema)`.
2. no `request.POST["_field"]` → `HttpResponse(status=400)`.
3. bind `schema.build_form(data=request.POST)`, run `is_valid()`, re-render just
   that one field's wrapper (with its error slot).
4. `_field` names no field → `Http404("Unknown field")`.

## `WizardView` (`wizards/wizard.py`)

Subclasses `formtools.SessionWizardView`. You subclass `WizardView`, set
`steps_config`, and implement `done()`. Full detail: [wizards.md](wizards.md).

- `__init_subclass__` derives `form_list` and `file_storage` from `steps_config`
  — **do not set `form_list`**.
- `as_view()` raises `RuntimeError` without `django-formtools`.
- `done()` — required override; base raises `NotImplementedError`.
- `render_done()` — do not override; it re-validates every prior step and
  promotes an htmx 3xx to a browser redirect.

## Panel views (`panels/pages.py`)

> This area is under active development. [panels.md](panels.md) has the current
> detail; the structure below is stable.

You do not instantiate these — `Panel.mount()` binds them per resource with the
`panel` and `resource` attributes injected. The class hierarchy:

```text
TemplateView
├── PanelPage                       non-resource pages (dashboards, custom pages)
│   └── DashboardPage               a widget grid; override widgets(self, request)
└── _ResourcePage                   base for resource CRUD; runs panel guards + resource.can()
    ├── ListRecords(TableMixin, _ResourcePage)   list page — override get_table()
    ├── _FormPage                   create/edit — builds schema.build_form, calls process_images
    │   ├── CreateRecord            action = "add"
    │   └── EditRecord              action = "change"
    ├── ViewRecord                  action = "view"; renders build_infolist(...)
    └── DeleteRecord                action = "delete"
```

Key facts:

- **`dispatch` runs the panel guards first, then `resource.can(request, action,
  obj)`** — a `PermissionDenied` from either propagates before the view body.
- **`ListRecords` MRO is `ListRecords → TableMixin → _ResourcePage →
  TemplateView`** — `TableMixin` before `_ResourcePage` so its `get()` chains to
  `TemplateView.get()`, but auth still runs first (in `dispatch`).
- Each page's `action` class attribute must be a Django permission verb —
  `"add"`, `"change"`, `"delete"`, `"view"` — because `Resource.perm(action)`
  interpolates it into `f"{app_label}.{action}_{model_name}"`. Note
  `CreateRecord.action = "add"` and `EditRecord.action = "change"` (not
  `"create"` / `"edit"`).
- Custom non-resource pages subclass **`PanelPage`** (public;
  `_PanelPage` is a deprecated alias) and are registered via `Panel.pages([...])`.

## Concern mixins (`core/concerns.py`)

Compose these into a `Component` subclass, **left** of `Component` in the base
list, to add fluent setters. Each setter stashes into `_config` and returns
`Self`.

| mixin | setters added |
|---|---|
| `HasLabel` | `.label`, `.help_text`, `.placeholder` |
| `HasHint` | `.hint`, `.icon` |
| `HasState` | `.required`, `.disabled`, `.readonly` (all default `True`), `.default(value)` |
| `HasColumnSpan` | `.column_span(int\|str)` (`@setter`); `.column_span_full()` (**plain method** — not a kwarg) |
| `HasChildComponents` | `.schema(list)` / `.components(list)` (aliases; **plain methods** — set `_children`, cannot be kwargs) |

`Field` = `HasLabel, HasHint, HasState, HasColumnSpan, Component`.
`Layout` = `HasChildComponents, Component`.

Everything on `Component` itself — `.extra_attributes`, `.visible`, `.hidden`,
`.when`, `.hidden_when`, `get_view_data`, `render` — is in
[architecture.md](architecture.md).
