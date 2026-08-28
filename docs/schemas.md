# Schemas (forms)

A `Schema` describes a form's **layout and presentation**. It decorates an
existing Django `Form` / `ModelForm` (or a model, via `modelform_factory`) — it
never validates. There is exactly one validation path: Django's.

```python
from django_cotton_components.schemas import (
    Schema, Section, Grid, TextInput, Textarea, Select, MultiSelect, Toggle, FileUpload,
)

def article_schema():
    return (
        Schema.make()
        .model(Article, fields=["title", "slug", "body", "status", "cover", "published_at"])
        .schema([
            Section.make("Content").schema([
                TextInput.make("title").required(),
                TextInput.make("slug").help_text("Lowercase, dashes."),
                Textarea.make("body"),
            ]),
            Section.make("Publishing").schema([
                Grid.make().columns(2).schema([
                    Select.make("status").searchable(),
                    TextInput.make("published_at").visible_when("status", equals="live"),
                ]),
                FileUpload.make("cover").image().max_size("2mb").max_dimensions(2000, 2000)
                    .convert("webp"),
            ]),
        ])
    )
```

`.form(FormClass)` decorates a hand-written form instead of `.model(...)`.
`.strict()` renders **only** the fields you declared (otherwise unmapped form
fields are appended as plain inputs).

## Rendering

From a `CreateView` / `UpdateView` use `SchemaFormMixin`:

```python
from django_cotton_components.mixins import SchemaFormMixin

class ArticleCreateView(SchemaFormMixin, CreateView):
    model = Article
    template_name = "articles/form.html"
    def get_schema(self):
        return article_schema()
```

```django
{% load dcc_tags %}
{% dcc_form schema %}          {# full <form> incl. CSRF, submit button #}
```

Or render just the fields (you supply the `<form>`): `{{ schema.render(request=request, form=form) }}`.

Panels and action modals build a standalone form from the declared fields with
`schema.build_standalone_form(...)` — same bind/render path, no full-form leak.

## Fields

| field | notes |
|---|---|
| `TextInput`, `EmailInput`, `PasswordInput` | `input_type` varies |
| `Textarea` | multi-line |
| `Hidden` | rendered as `<input type=hidden>` |
| `Select`, `MultiSelect`, `Radio` | `.options([(v, label), …])` or inferred from the model field; `.searchable()` adds a filter box (`MultiSelect` is searchable by default) |
| `Checkbox`, `Toggle` | boolean; `Toggle` is a switch |
| `FileUpload` | `.image()`, `.accept("…")`, `.max_size("2mb")`, `.min_dimensions(w,h)`, `.max_dimensions(w,h)`, `.aspect_ratio("16:9")`, `.resize(max_width=…)`, `.convert("webp", quality=82)`, `.strip_exif()`, `.allow_svg()` — see [images.md](images.md) |

Common setters (any field): `.label(...)`, `.help_text(...)`, `.placeholder(...)`,
`.required()`, `.disabled()`, `.readonly()`, `.default(value)`,
`.column_span(n)` / `.column_span_full()`.

### Conditional visibility

`.visible_when("other_field", equals="live")` (or `is_in=[...]`, or bare for
truthy) compiles to an Alpine `x-show` that re-evaluates live as siblings change
— no round-trip. Requires JS; with JS off the field just shows.

### Live validation

`.live()` (or `.live(400)` ms) posts the single field to the schema-validate
endpoint on change and swaps its error slot.

## Layout

`Section` (titled block), `Grid` (`.make(columns=2)`), `Fieldset`, `Tabs` / `Tab`.
All take `.schema([...])` of child fields or nested layouts.
