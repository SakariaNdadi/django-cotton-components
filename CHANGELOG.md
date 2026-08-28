# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versioning is
[SemVer](https://semver.org/) (0.x permits breaking changes).

## [1.0.0b1] — unreleased

Complete rebuild. The package moves from a set of hand-authored cotton templates
to a Python component layer (Filament-inspired) that drives `django.forms`.

### Changed

- **`Resource.permission_prefix` semantics.** It now supplies only the *prefix*
  of the permission string (the app label, and optionally the model name when it
  contains a dot); the action (`view` / `add` / `change` / `delete`) is always
  appended. Previously a non-empty `permission_prefix` replaced the whole
  permission and dropped the action, so every action collapsed to one
  permission. A resource relying on the old behaviour must move to a custom
  `can()` override.

### Security

- A stored spec column/entry named after a model method Django flags
  `alters_data` (`delete`, `save`, …) no longer invokes it on every row render —
  the value resolves to empty. Dotted display paths also refuse private
  (`_`-prefixed) segments. New shared helper `core.paths.traverse`.
- `validate_spec` now rejects a stored spec above 64 KB or nested deeper than 8
  levels.

### Fixed

- Client-mode tables: row selection and the bulk-action toolbar are now live
  (the shared selection state was never wired into the client engine, and
  `selectedCount`/`allSelected` were frozen by an object spread).
- Bulk action `hx-include` selected zero records (`closest .dcc-table [x]:checked`
  resolves to `elt.closest()` and is always null) — the ticked pks now ride as
  hidden inputs.
- Quick-edit / `.modal(schema)` actions bound the whole `ModelForm` and always
  failed validation; they now bind only the declared fields, and a successful
  modal action closes the dialog.
- A non-searchable `<c-dcc.form.select>` no longer renders its filter box.
- Table width no longer changes with the result count (`<table>` was
  `display:block`); the actions cell no longer offsets its bottom border.

### Added

- `htmx.boost()` and `htmx.oob()` attribute-bag helpers.
- `{% dcc_assets %}` loads the Alpine `focus` plugin (opt out with `focus=False`)
  so modal / drawer `x-trap` focus containment works.
- Tables — `Table.record_url(fn)` (whole-row click → full-page nav),
  `.record_action(Action)` (row click → modal / navigate), `.record_preview(fn)`
  (hover card); `Action.collapsed()` folds a row action into a "⋯" menu;
  `.presentation("feed")` renders rows as a borderless list;
  `.pagination_position("left"|"center"|"right")`; `.infinite_scroll()`;
  a **"Rows per page"** picker appears when `.paginate([…])` is passed with >1
  choice (otherwise the size is a fixed 10).
- `Schema.build_standalone_form()` — bind only the declared fields (action
  modals, filter forms) instead of the whole `ModelForm`.
- Component docs: `docs/schemas.md`, `docs/actions.md`, `docs/wizards.md`,
  `docs/ui.md`, `docs/images.md`, and a `docs/` index.
- `django_cotton_components.ui` — canonical primitives (`Button`, `IconButton`,
  `Badge`, `Icon`, `Checkbox`, `Modal`, `Menu`), one component + one leaf
  template each; every subsystem composes them instead of hand-rolled markup.
- `django_cotton_components.icons` — swappable icon-set registry
  (`DCC["ICON_SET"]`), Font Awesome default; `{% dcc_icon %}`, `<c-dcc.icon>`.
- `django_cotton_components.infolists` — read-only counterpart to a schema
  (`Infolist`, `TextEntry` / `BadgeEntry` / `BooleanEntry` / `DateEntry`).
- `django_cotton_components.panels` — dashboard **widgets** (`StatWidget`,
  `ChartWidget`, `TableWidget`), `DashboardPage`, `Panel.pages([...])` for custom
  pages, and a `delete` action + route on every resource.
- `django_cotton_components.studio` (separate app) — build a `Resource` from a
  stored `DashboardSpec` JSON row: type registries, `*_from_spec` deserializers
  (no import paths, no callables), `DynamicResource`, `Panel.dynamic()`.
- Tables: keyset (cursor) pagination — `.stream()` (default server mode), no
  `COUNT(*)` / `OFFSET`, append-on-scroll fragments; `.page_numbers()` opts back
  in. Bulk "select every matching row" hands the callback the filtered queryset.
- `{% dcc_assets %}` now emits htmx and the icon stylesheet (`htmx=` / `icons=`
  opt-outs); the wizard swaps steps over htmx.
- `django_cotton_components.schemas` — fluent form builders (`Schema`, `Section`,
  `Grid`, `Tabs`, `Fieldset`, and field components) that decorate an existing
  Django `Form` / `ModelForm`. `Schema.to_form_class()` for standalone use.
- `django_cotton_components.core` — `Component` primitive, closure evaluation,
  frozen `RenderContext`, `AttributeBag` (merges `class`, never replaces).
- `django_cotton_components.tables` — `Table` with automatic client-side
  (zero-request) / server-side (htmx) rendering by row count, `Column`
  subclasses, filters, injection-safe sort/search, `TableMixin`.
- `django_cotton_components.actions` — `Action` / `BulkAction`, a key-addressed
  registry (never an import path from the client), authorize-at-render *and*
  at-execute, bulk targets re-scoped to the owner's filtered queryset.
- `django_cotton_components.wizards` — `WizardView` on `django-formtools`
  (`dcc[wizard]`), one DCC schema per step, per-step Django validation.
- `django_cotton_components.panels` — `Resource` + `Panel` mounting list /
  create / edit / view pages under their own URL namespace, separate from
  `django.contrib.admin`.
- `django_cotton_components.images` — Pillow-backed upload validation and
  processing, pluggable `ThumbnailBackend`.
- `django_cotton_components.htmx` — single adapter emitting every `hx-*`
  attribute so an htmx-4 migration is one file.
- Toast notifications driven by `HX-Trigger`.
- `{% dcc_assets %}` template tag; prebuilt stylesheet at
  `static/dcc/dcc.css` and small Alpine helpers at `static/dcc/dcc.js`.
- uv + hatchling packaging, `src/` layout, nox sessions, CI matrix.

### Changed / Breaking
- Import package unchanged (`django_cotton_components`); every template tag and
  prop is new. See [MIGRATION.md](MIGRATION.md).
- Templates moved to `templates/cotton/dcc/…`; `dcc_` filename prefix dropped.
- Styling moved from inline Tailwind utility chains to semantic `dcc-*` classes.
- `requires-python` raised to `>=3.12`; Django `>=5.2`; django-cotton `>=2.7,<3`.

### Removed
- `dcc_table.html` — replaced by the server/client dual-mode table builder
  (Phase 3). It shipped every model field of every row to the browser.
- `Pipfile`, `Pipfile.lock`, `MANIFEST.in`.

### Deprecated
- `{% get_field_errors %}` — kept for one minor release; the forms bridge renders
  field errors directly.
