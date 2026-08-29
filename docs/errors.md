# Errors

Every exception the library raises, and exactly what triggers it. Use this when
a stack trace surfaces one of these types.

## Hierarchy

```text
Exception
└── DCCError                       core/exceptions.py — base for every library error
    ├── SchemaError                a schema references a field the form does not have
    ├── ThumbnailBackendError      DCC["THUMBNAIL_BACKEND"] could not be imported
    └── ClosureInjectionError      a config closure declared a non-injectable parameter

django.core.exceptions.ValidationError
└── ImageValidationError           an uploaded image failed validation
    (also the studio raises plain ValidationError — see no-code.md)
```

Catch `DCCError` to catch every library-specific error at once. `ImageValidationError`
is deliberately **not** a `DCCError` — it is a Django `ValidationError` so it
surfaces as a normal form error.

## `DCCError` subclasses

### `SchemaError`

> `Schema references fields not on <FormName>: [...]. Available: [...]`

Raised by `forms_bridge.check_alignment` when a field you declared in a schema
(`TextInput.make("naem")`) is not present on the bound Django form. Fired from
`Schema.build_form()` and from `Schema.render(form=...)` — so a schema that
renders fine unbound can raise the moment you pass a narrower form.

**Fix:** correct the field name, add the field to the form, or (for a
deliberately partial form) use `build_standalone_form` / `.strict()`.

### `ThumbnailBackendError`

> `Cannot import THUMBNAIL_BACKEND '<path>'`

Raised by `get_thumbnail_backend()` when `DCC["THUMBNAIL_BACKEND"]` is set to a
dotted path that `import_string` cannot resolve. This is the **only** trigger —
an empty thumbnail result does not raise (a table's `ImageColumn` also swallows
any backend exception and falls back to the original URL).

### `ClosureInjectionError`

> `<fn> requests ['reqeust']; injectable names are ['component', 'context', 'form', 'get', 'operation', 'record', 'request', 'set', 'state', 'user']`

Raised by `evaluate()` at render time when a configuration closure declares a
parameter name that is not injectable — including a typo. Applies to any closure
passed to a `@setter` that goes through `evaluate` (`.label(fn)`, `.visible(fn)`,
`.state(fn)`, `Table.record_url(fn)`, widget `.value(fn)`, …).

**Not** raised by `Action.action(fn)` — that callback uses a plain parameter
match and an undeclared name is a normal `TypeError` from the call.

## `ImageValidationError`

A `django.core.exceptions.ValidationError` subclass, raised by `validate_image`
(so it renders as a form field error, not a 500). Messages:

| message | condition |
|---|---|
| `File is larger than <n> bytes.` | over `.max_size(...)` — checked first, before SVG |
| `SVG uploads are rejected by default …` | an SVG without `.allow_svg()` |
| `Pillow is required for image fields. …` | PIL not installed on an image field |
| `Image exceeds the pixel limit.` | over `DCC["IMAGE_MAX_PIXELS"]` (decompression bomb) |
| `File is not a valid image.` | Pillow cannot decode it |
| `Image must be at least <w>x<h>px.` / `Image must be at most <w>x<h>px.` | outside `.min_dimensions` / `.max_dimensions` |
| `Image aspect ratio is out of range.` | outside `.aspect_ratio` ± `.aspect_tolerance` |

## Plain Python exceptions

| exception | where | condition |
|---|---|---|
| `TypeError(f"{cls} has no setter {key!r}. Valid: [...]")` | `Component`, `Column` constructors | an unknown kwarg (no matching `@setter`) |
| `TypeError(f"{cls} has no setter {key!r}")` | `Action`, `Filter`, `Widget` constructors | same, shorter message |
| `TypeError("Tabs.schema() accepts only Tab instances")` | `Tabs.schema([...])` | a non-`Tab` child |
| `TypeError` (from the call) | `Action.run` | the `.action(fn)` callback declares a parameter that is not `request`/`user`/`data`/`record`/`records` |
| `ValueError(f"{Field} requires a field name")` | any `Field` subclass constructor | `name` is `None` |
| `ValueError(f"{cls} has no template_name")` | `render_component` | a component subclass left `template_name` empty |
| `ValueError("Schema needs .form(FormClass) or .model(Model) before rendering")` | `Schema.get_form_class()` | neither `.form()` nor `.model()` was called |
| `ValueError(f"{View} needs a `schema` or `get_schema()`")` | `SchemaFormMixin.get_schema()` | `schema` is `None` and `get_schema` not overridden |
| `ValueError(f"{View} needs a `table` or `get_table()`")` | `TableMixin.get_table()` | `table` is `None` and `get_table` not overridden |
| `ValueError(f"Unsafe attribute name: {key!r}")` | `AttributeBag.set()` | key is empty or contains whitespace or any of `" ' > / =` |
| `ValueError(f"ChartWidget.kind must be one of [...]")` | `ChartWidget.kind(...)` | a kind outside `{line, bar, area, pie, doughnut, radar}` |
| `AssertionError("Action not bound to an owner")` | `Action.url()` | called before `bind_owner()` — the action is not exposed by a registered owner |
| `RuntimeError("WizardView needs django-formtools. …")` | `WizardView.as_view()` | the `[wizard]` extra is not installed |
| `NotImplementedError("Implement done() to persist the collected data.")` | `WizardView.done()` | the base method was not overridden |
| `AttributeError(f"Unknown DCC setting: {name!r}. …")` | `dcc_settings.<name>` | a mistyped `DCC` key |
| `KeyError(f"Unknown {kind} type {name!r}. Registered: [...]")` | `TypeRegistry.get()` | a studio spec named a type nobody registered |

## HTTP responses from the endpoints

Not exceptions — status codes the internal views return.

| view | status | condition |
|---|---|---|
| `ActionView` | `404` | unknown owner key or action name (`registry.resolve` → `None`) |
| `ActionView` | `403` | `action.is_authorized(...)` false — on GET **and** on POST |
| `ActionView` | `200` (empty body) | a modal action succeeded — htmx clears the mount, dialog closes |
| `ActionView` | `204` | an inline action succeeded — the row is not blanked |
| `ActionView` | `200` (modal re-rendered) | the schema form failed validation |
| `SchemaValidateView` | `404` | unknown schema key, or `_field` names no field in the schema |
| `SchemaValidateView` | `400` | the `_field` POST parameter is missing |

Successful action responses carry `HX-Trigger: {"dcc:toast": ..., "dcc:refresh":
true}`.
