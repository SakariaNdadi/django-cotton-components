# django-cotton-components

Filament-inspired schema, table, and action builders for Django. Declare UI in
Python; it renders itself through [django-cotton](https://django-cotton.com/),
wired to real `django.forms` validation.

> **1.0.0b1** — a full rebuild. The old prop-driven cotton templates are gone.
> See [MIGRATION.md](MIGRATION.md) and [CHANGELOG.md](CHANGELOG.md).

## Status

| Area | State |
|---|---|
| UI primitives (`Button`, `Badge`, `Icon`, `Checkbox`, `Modal`, `Menu`) + icon-set registry | ✅ |
| Form schemas (`Schema`, `Section`, `Grid`, `Fieldset`, `Tabs`, fields) | ✅ |
| django.forms bridge (decorate a `Form`/`ModelForm`, real validation) | ✅ |
| Reactive searchable `Select` / `MultiSelect`; conditional visibility (zero requests) | ✅ |
| Image upload + Pillow validation + processing + thumbnails | ✅ |
| `htmx.py` adapter — every `hx-*` from one file | ✅ |
| Tables — auto client/server by row count; **keyset streaming** over millions (no `COUNT`) | ✅ |
| Actions (row / bulk / modal / page), key-addressed, authorize twice; select-all-matching bulk | ✅ |
| Wizard (`dcc[wizard]`, django-formtools) — **htmx step swapping** | ✅ |
| Panels / Resources (list · create · edit · view · **delete**), admin-independent | ✅ |
| Infolists; dashboard **widgets** + `DashboardPage`; custom pages | ✅ |
| No-code resources from stored JSON (`django_cotton_components.studio`) | ✅ |
| Global search, relation managers, a visual dashboard builder | 🔜 |

## Docs

[Schemas / forms](docs/schemas.md) · [Tables](docs/tables.md) ·
[Actions](docs/actions.md) · [Wizards](docs/wizards.md) ·
[UI primitives](docs/ui.md) · [Images](docs/images.md) ·
[Panels & Resources](docs/panels.md) · [Infolists](docs/infolists.md) ·
[No-code resources](docs/no-code.md) — index: [docs/](docs/README.md)

## Install

```bash
pip install "django-cotton-components[images]"
```

```python
INSTALLED_APPS = [
    # ...
    "django_cotton",  # before django_cotton_components
    "django_cotton_components",
]
```

Add `{% dcc_assets %}` to your base template `<head>` — it emits the stylesheet,
the small Alpine helpers, htmx, Alpine and the icon-set stylesheet. Pass
`htmx=False` / `alpine=False` / `icons=False` for anything the host page already
loads. For the no-code seam, also add `"django_cotton_components.studio"`.

## Quick start

```python
from django_cotton_components.schemas import Schema, Section, Select, TextInput, Toggle


def article_schema():
    return (
        Schema.make()
        .form(ArticleForm)  # your existing ModelForm
        .schema(
            [
                Section.make("Content")
                .columns(2)
                .schema(
                    [
                        TextInput.make("title").required().column_span_full(),
                        Select.make("status").searchable(),
                        TextInput.make("slug"),
                    ]
                ),
                Section.make("Publishing").schema(
                    [
                        Toggle.make("featured"),
                        TextInput.make("published_at").visible_when("status", equals="live"),
                    ]
                ),
            ]
        )
    )
```

```python
from django.views.generic import CreateView
from django_cotton_components.mixins import SchemaFormMixin


class ArticleCreateView(SchemaFormMixin, CreateView):
    model = Article
    template_name = "articles/form.html"

    def get_schema(self):
        return article_schema()
```

```django
{# articles/form.html #}
<form method="post" enctype="multipart/form-data">
  {% csrf_token %}
  {{ schema_html }}
  <button class="dcc-btn dcc-btn--primary">Save</button>
</form>
```

The schema **never validates** — your Django form does. Field labels, help text,
choices and `required` are inherited from the form unless you override them.
Submitting with JavaScript disabled still works: every control is a real,
correctly-named HTML input.

### Fluent or kwargs — same object

```python
TextInput.make("email").label("Email").required()
TextInput("email", label="Email", required=True)  # identical
```

## How rendering stays cheap

htmx is used only for mutations and for data the client does not have. A rendered
form issues **zero** background requests: conditional fields toggle via a compiled
Alpine expression, errors render server-side, `Select` filters options already in
the page. Opt into a debounced round-trip per field with `.live()`.

## Styling

Components emit semantic `dcc-*` classes and ship a dependency-free stylesheet
(design tokens as CSS custom properties, light/dark aware). To theme or purge
with Tailwind 4, point a build at [`css/dcc.css`](css/dcc.css) instead.

## Development

```bash
uv sync
uv run pytest -q
uv run nox -s lint typecheck coverage
uv run --project example python example/manage.py migrate
uv run --project example python example/manage.py seed
uv run --project example python example/manage.py runserver
```

## License

MIT. Component styling adapted from Penguin UI; original cotton scaffolding by
BugBytes.
