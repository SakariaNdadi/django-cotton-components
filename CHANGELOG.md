# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versioning is
[SemVer](https://semver.org/) (0.x permits breaking changes).

## [1.0.0b1] — unreleased

Complete rebuild. The package moves from a set of hand-authored cotton templates
to a Python component layer (Filament-inspired) that drives `django.forms`.

### Added
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
