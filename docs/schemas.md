# Schemas (forms)

## Mental model

A `Schema` describes a form's **layout and presentation**. It decorates an
existing Django `Form` / `ModelForm` (or a model, via `modelform_factory`).

**A schema never validates.** There is exactly one validation path — Django's
form (`schemas/schema.py:21-26`). Field labels, help text, choices and `required`
are inherited from the form unless you override them per field. Every control is
a real, correctly-named HTML input, so submitting with JavaScript disabled still
works and still validates.

Why this split: layout and validation change for different reasons and at
different times. Keeping the schema out of validation means there is never a
second set of rules to keep in sync, and a schema can safely render a *subset* of
a large form (a wizard step, an action modal) without the hidden fields failing
validation.

## Quick start

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
                Textarea.make("body").column_span_full(),
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

Render from a `CreateView` / `UpdateView` with `SchemaFormMixin`:

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
{% dcc_form schema %}          {# full <form> incl. CSRF + submit button #}
```

Or render just the fields inside your own `<form>`:
`{{ schema.render(request=request, form=form) }}`.

## `Schema` — configuration

All configuration methods are **fluent-only** (not `@setter` — you cannot pass
them as `Schema()` kwargs) and return `self`.

| Method | Effect |
|---|---|
| `Schema.make()` | construct |
| `.form(FormClass)` | decorate a hand-written `Form` / `ModelForm` |
| `.model(Model, *, fields="__all__")` | decorate a model — builds a `ModelForm` via `modelform_factory` |
| `.schema([...])` / `.components([...])` | the tree of fields and layout containers (aliases; identical) |
| `.strict(value=True)` | render **only** the fields you declared |

**`.form()` vs `.model()` — do not rely on both.** `get_form_class()` returns
`_form_class` if set, otherwise builds one from `_model`
(`schemas/schema.py:68-73`). Calling `.model()` after `.form()` has no effect.
Calling neither raises `ValueError("Schema needs .form(FormClass) or .model(Model)
before rendering")` at first render.

**`.strict()` — what it changes.** By default the schema appends every form field
you did *not* name — as a `<input type=hidden>` if the widget is hidden, else a
plain `TextInput` (`schemas/schema.py:157-168`). This keeps a `ModelForm` valid
even if you forgot a required field. `.strict()` disables the append: unnamed
fields are neither rendered nor submitted, so a required one that you omitted
will fail validation on save. Use `.strict()` for deliberately partial forms
(wizard steps, modals).

## `Schema` — methods you call

| Method | Returns | Use |
|---|---|---|
| `get_form_class()` | `type[BaseForm]` | the Django form class this schema validates through |
| `is_modelform()` | `bool` | whether that class is a `ModelForm` |
| `to_form_class()` | `type[BaseForm]` | a real Django form with **only the declared fields** — used by wizard steps, action modals, filter forms |
| `build_form(*args, **kwargs)` | `BaseForm` | bind the **full** form; runs `check_alignment` (see errors) and attaches image validators. Pops `instance=` if not a `ModelForm`. |
| `build_standalone_form(*args, **kwargs)` | `BaseForm` | bind a form of **only declared fields** (`to_form_class()` path); attaches image validators, no alignment check |
| `image_specs()` | `dict[str, dict]` | field name → image spec, for every `FileUpload` |
| `process_images(instance)` | `None` | run the resize/convert/strip-exif pipeline for every `FileUpload` field, then `instance.save()`. **Call after `form.save()`.** `SchemaFormMixin` and panel resources do this for you. |
| `iter_fields()` | `Iterator[Component]` | flattens layout containers to leaf fields |
| `render(*, request=None, form=None, record=None, operation="create")` | `SafeString` | the fields only (you supply `<form>`) |
| `render_form(*, request=None, form=None, record=None, action="", submit_label="Save", show_actions=True)` | `SafeString` | a complete `<form>` incl. CSRF; `enctype="multipart/form-data"` when the form is multipart |

`render()` with `form=None` builds the form itself (`build_form(instance=record)`).
Pass a `form` to render your view's bound instance (with errors).

## Fields

Import from `django_cotton_components.schemas`.

| Field | Notes |
|---|---|
| `TextInput` | `input_type="text"` |
| `EmailInput` | `TextInput` subclass, `input_type="email"` |
| `PasswordInput` | own template with a reveal toggle; does not delegate to the Django widget |
| `Textarea` | multi-line |
| `Hidden` | `<input type=hidden>`; label suppressed |
| `Checkbox` | boolean; label rendered by the control, `value="on"` |
| `Toggle` | `Checkbox` subclass rendered as a switch (`role="switch"`) |
| `Select` | single choice |
| `MultiSelect` | multiple choice; **`.searchable()` defaults to `True`** unless you set it explicitly |
| `Radio` | single choice as a radio group |
| `FileUpload` | see [images.md](images.md) |

### Choice options

`Select` / `MultiSelect` / `Radio`:

- `.options([(value, label), …])` or `.options({value: label})` — an explicit list.
- With no `.options(...)`, options come from the bound model field's `choices`
  (empty / `None` values skipped).
- `.searchable()` adds a client-side filter box over the options already in the
  page — no request.

### Common field setters

Every field, via the concern mixins ([architecture.md](architecture.md#the-fluent--kwargs-duality)):

| Setter | From | Note |
|---|---|---|
| `.label(str \| None \| fn)` | `HasLabel` | `None` suppresses an inherited label |
| `.help_text(...)`, `.placeholder(...)` | `HasLabel` | |
| `.hint(...)`, `.icon(...)` | `HasHint` | |
| `.required()`, `.disabled()`, `.readonly()` | `HasState` | default arg `True`; each accepts a bool or a closure |
| `.default(value)` | `HasState` | used as the value when no form is bound |
| `.column_span(n)` | `HasColumnSpan` | `@setter` |
| `.column_span_full()` | `HasColumnSpan` | **fluent-only** — not a kwarg |
| `.extra_attributes({...})` | `Component` | merges; `class` appends |
| `.visible(bool\|fn)` / `.hidden(bool\|fn)` | `Component` | server-side; a hidden field renders `""` |
| `.when(cond)` / `.hidden_when(cond)` | `Component` | fluent-only aliases of `visible` / `hidden` |
| `.visible_when("other", equals=…)` | `Field` | **fluent-only**; client-side, reactive (below) |
| `.live(ms=400)` | `Field` | opt-in per-field server validation (below) |

`.required()` / `.disabled()` here only affect **rendering**. Validation still
comes from the Django field. To actually make a field required, set it on the
form.

### Conditional visibility — `.visible_when(...)`

Compiles a small predicate to an Alpine `x-show` that re-evaluates live as
sibling fields change — **no round-trip** (`schemas/visibility.py`).

```python
TextInput.make("published_at").visible_when("status", equals="live")
Select.make("plan").visible_when("kind", is_in=["pro", "enterprise"])
Toggle.make("newsletter").visible_when("accepted_terms")   # bare = truthy
```

Only these three forms compile. Anything more complex: use a plain Python closure
in `.visible(fn)` (evaluated once at render, **not** reactive), or a `.live()`
round-trip. Multiple `.visible_when(...)` calls on one field are AND-ed. With
JavaScript off the field simply shows.

### Live validation — `.live()`

`.live()` (or `.live(400)` ms) posts the single field to the schema-validate
endpoint on `change` and swaps that field's error slot. The debounce defaults to
`DCC["LIVE_VALIDATION_DEBOUNCE_MS"]` (400). Requires the schema to be registered
with a key (`register_schema`) and the `dcc/` URLs mounted; see
[views-and-mixins.md](views-and-mixins.md#schemavalidateview). Without `.live()`
a rendered form issues **zero** background requests.

## Layout containers

`Section`, `Grid`, `Fieldset`, `Tabs` / `Tab`. All take `.schema([...])` of child
fields or nested layouts (fluent-only). All support `.visible()` / `.hidden()`.

| Container | Template role | Setters |
|---|---|---|
| `Section` | titled block | `.columns(n)` (default 1), `.description(str)` |
| `Grid` | column grid | `.columns(n)` (default 2) |
| `Fieldset` | `<fieldset>` | `.columns(n)` (default 1) |
| `Tab` | one tab body | — (use inside `Tabs`) |
| `Tabs` | tab strip + panels | — |

**`Tabs.schema()` accepts only `Tab` instances** — anything else raises
`TypeError("Tabs.schema() accepts only Tab instances")` (`schemas/layout.py:101-106`).

`Section.make("Title")` — the positional argument is the title. `Grid.make()`
takes no title.

## Views & mixins

### `SchemaFormMixin` (`mixins.py:14-49`)

Drives a `FormView` / `CreateView` / `UpdateView` from a schema.

- **MRO:** place `SchemaFormMixin` **left** of the Django generic view. It calls
  `super().get_context_data()` and `super().form_valid()` and reads
  `self.object` / `self.request`.
- **Class attribute:** `schema: Schema | None = None`.
- **Override `get_schema(self) -> Schema`** to build the schema per request.
  Returning `self.schema` when it is `None` raises
  `ValueError(f"{type(self).__name__} needs a `schema` or `get_schema()`")`.
- `get_form_class()` returns `get_schema().get_form_class()` — you do not set
  `form_class`.
- `get_context_data()` adds `schema` and `schema_html` (rendered with the bound
  `context["form"]` and `self.object`).
- `form_valid()` calls `super().form_valid(form)` then, **only if `self.object`
  is set and the schema has image specs**, runs `schema.process_images(instance)`.
  So image processing happens on `CreateView` / `UpdateView`, not a bare
  `FormView`.

Do not override `get_form_class` or `form_valid` unless you also replicate the
image step.

### `SchemaValidateView`

The endpoint behind `.live()`. See [views-and-mixins.md](views-and-mixins.md).

## Rendering outside a view

```django
{% load dcc_tags %}
{% dcc_form schema %}                       {# full <form> from the context's `form` #}
{% dcc_form schema form=my_other_form %}    {# explicit bound form #}
```

Panels and action modals build a standalone form from the declared fields with
`schema.build_standalone_form(...)` — same bind/render path, no full-form leak.

## Callbacks

Any field setter can take a closure. Injected by parameter name from
`{record, request, user, form, operation, context, component, get, state}` — see
[callbacks.md](callbacks.md). `get("other_field")` reads the current bound value
of a sibling, so `.label(lambda get: "Ship to " + (get("country") or "?"))`
works.

## Constraints / do not combine

- `.form()` and `.model()` — `.form()` wins; don't expect `.model()` after it to
  do anything.
- `.strict(True)` + omitting a required form field → validation fails on save
  with no visible input to fix it. Either declare the field or drop `.strict()`.
- `Tabs.schema([...])` — `Tab` instances only.
- `Field(name=None)` → `ValueError("<Field> requires a field name")`. Every field
  needs a name.
- `.visible_when(...)` is client-side and reactive; `.visible(fn)` is server-side
  and evaluated once. They are different tools — don't expect `.visible(fn)` to
  react to form edits.
- A declared field name that is not on the Django form → `SchemaError` at
  `build_form` / `render` time (see [errors.md](errors.md)).

## Settings

| Key | Default | Effect |
|---|---|---|
| `LIVE_VALIDATION_DEBOUNCE_MS` | `400` | default debounce for `.live()` |

## Known sharp edges

- `MultiSelect` is searchable by default; `Select` is not. Pass
  `.searchable(False)` to opt out.
- `.required()` on a field is cosmetic — it draws the marker; it does not add a
  validator.
- A schema built from `.model(Model, fields=[...])` still validates every field
  the generated `ModelForm` includes. If you list fewer `fields` than you render,
  the extra rendered ones must exist on the model.
- `render(form=...)` re-runs `check_alignment` every call; a schema that renders
  fine unbound can raise `SchemaError` the moment you pass a narrower form.
