# Documentation

Declare UI in Python; it renders itself through django-cotton, wired to real
`django.forms` validation. These docs aim to be complete enough that you never
need to read `src/` to build with the library.

**Start with [architecture.md](architecture.md)** — the render pipeline,
`RenderContext`, the fluent/kwargs duality, closures, the design invariants. Every
other doc assumes it.

## Reference (cross-cutting)

| doc | what |
|---|---|
| [architecture.md](architecture.md) | how a component becomes HTML; `RenderContext`; `UNSET`; `AttributeBag`; the `htmx.py` choke point; string-keyed registries; template tags; the four design invariants |
| [settings.md](settings.md) | install, `INSTALLED_APPS` order, `{% dcc_assets %}`, URL mount, every `DCC[...]` key, system checks |
| [views-and-mixins.md](views-and-mixins.md) | every view + mixin, MRO rules, override vs leave-alone, the concern mixins |
| [callbacks.md](callbacks.md) | every user-supplied callable, `evaluate()` injection vs the action-callback match, per-call-site contracts |
| [errors.md](errors.md) | every exception + its trigger condition; the endpoint status codes |

## Subsystems

| doc | what |
|---|---|
| [schemas.md](schemas.md) | `Schema` — form layout over a Django `Form` / `ModelForm`; fields, layout, conditional visibility, live validation |
| [tables.md](tables.md) | `Table` — columns, filters, client/server mode, keyset streaming, selection & bulk actions, row-click, hover preview, feed presentation |
| [actions.md](actions.md) | `Action` / `BulkAction` — key-addressed operations, modals, callbacks, authorize-twice, select-all-matching |
| [infolists.md](infolists.md) | `Infolist` — the read-only counterpart to a schema |
| [wizards.md](wizards.md) | `WizardView` — multi-step forms over django-formtools with htmx step swapping |
| [ui.md](ui.md) | `Button`, `Badge`, `Icon`, `Checkbox`, `Menu`, `Modal` (Python **and** `<c-dcc.*>`) + the icon-set registry |
| [images.md](images.md) | `FileUpload` validation, the Pillow processing pipeline, thumbnails |
| [panels.md](panels.md) | `Panel` / `Resource` — an admin-independent CRUD surface; `DashboardPage` + widgets |
| [widgets.md](widgets.md) | dashboard widgets — `StatWidget`, `ChartWidget`, `BarListWidget`, `TableWidget`, custom widgets |
| [no-code.md](no-code.md) | resources and dashboards defined by stored configuration (`django_control_components.studio`) |
