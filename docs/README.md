# Documentation

Declare UI in Python; it renders itself through django-cotton, wired to real
`django.forms` validation.

| doc | what |
|---|---|
| [schemas.md](schemas.md) | `Schema` — form layout over a Django `Form` / `ModelForm`; fields, layout, conditional visibility, live validation |
| [tables.md](tables.md) | `Table` — columns, filters, client/server mode, pagination, selection & bulk actions, row-click, hover preview, feed presentation |
| [actions.md](actions.md) | `Action` / `BulkAction` — key-addressed operations, modals, callbacks, authorization |
| [wizards.md](wizards.md) | `WizardView` — multi-step forms over django-formtools with htmx step swapping |
| [ui.md](ui.md) | `Button`, `Badge`, `Icon`, `Checkbox`, `Menu`, `Modal` + the icon-set registry |
| [images.md](images.md) | `FileUpload` validation, the Pillow processing pipeline, thumbnails |
| [panels.md](panels.md) | `Panel` / `Resource` — an admin-independent CRUD surface; `DashboardPage` + widgets |
| [infolists.md](infolists.md) | `Infolist` — the read-only counterpart to a schema |
| [no-code.md](no-code.md) | resources defined entirely by a stored `DashboardSpec` JSON row |

Cross-cutting: every `hx-*` attribute is produced by `htmx.py` (migrating htmx
versions is a one-file change); the Python component layer renders leaf templates
directly and never touches django-cotton's `<c-…>` tag engine.
