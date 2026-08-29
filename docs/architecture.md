# Architecture

Read this once before the subsystem docs. Every builder in the library —
`Schema`, `Table`, `Action`, `Widget`, `Infolist`, the schema fields, the layout
containers — shares the machinery described here. The subsystem docs assume it.

## The one-sentence model

You declare UI as **Python objects that hold configuration only**; at request
time each object is handed a **`RenderContext`** and renders **one leaf Django
template** directly, producing escaped HTML. htmx is used only for mutations and
for data the browser does not already have.

## Why it is built this way

The 0.1.x line was prop-driven cotton templates. Two classes of bug killed it:
unescaped interpolation into `<c-…>` tag strings, and a table that shipped every
row's full model dict to the browser. 1.0 is a rebuild whose shape is a direct
response:

| Decision | Reason |
|---|---|
| Python objects render leaf templates via `render_to_string`, **never** round-trip through a `<c-…>` tag string (`core/renderer.py:14-20`) | The props are already a typed dict. Stringifying them into a tag is exactly where escaping bugs come from. |
| Component instances hold **configuration only**; per-request data flows through `RenderContext` (`core/component.py:49-51`, `core/context.py:17-22`) | One instance can render concurrently against different requests with no cross-talk. You can build a schema once at import time and reuse it. |
| Every `hx-*` attribute is produced by `htmx.py`; **no template contains a literal `hx-*`** (`htmx.py:1-7`) | Migrating htmx versions is a one-file change. A test greps the template tree to enforce it. |
| The client only ever sends **opaque string keys** (an owner key, an action name, a schema key, a spec slug) — never an import path, model label, or callable | An unknown key is a 404, not a stack trace. A tampered key cannot reach code that was not registered. |
| Validation is **always** Django's form (`schemas/schema.py:21-26`) | There is exactly one validation path. A schema decorates a `Form`/`ModelForm`; it never validates. |
| Modal and menu bodies are **pre-rendered HTML strings** | A lint test forbids `{{ }}` inside `x-data="{…}"` (see *Design invariants* below), so the Python render path has no slot mechanism to hand a template into an Alpine component. |

## The render pipeline

```text
Component.render(ctx)
  │  ctx not visible?  → SafeString("")            core/component.py:141-146
  ▼
render_component(component, ctx)                    core/renderer.py:13-26
  │  template_name empty?  → ValueError
  ▼
data = component.get_view_data(ctx)                 the subclass hook
  ▼
render_to_string(component.template_name, data, request=ctx.request)
  ▼
SafeString(html)
```

`get_view_data(ctx)` is the single hook a component subclass overrides. The base
returns `{"name", "attrs": AttributeBag, "component": self}` (`core/component.py:131-139`);
subclasses call `super().get_view_data(ctx)` and add keys their leaf template
needs. **Do not override `render`.**

## `RenderContext`

A frozen, slotted dataclass — per-request state for one render pass
(`core/context.py:15-49`).

| Field | Default | Meaning |
|---|---|---|
| `request` | `None` | the `HttpRequest` |
| `record` | `None` | the object being rendered (a model instance, a `dict`, a `SimpleNamespace`) |
| `form` | `None` | the bound Django form (schemas) |
| `operation` | `"create"` | `"create"` / `"edit"` / `"view"` |
| `parent` | `None` | the enclosing component, during child rendering |
| `extra` | `{}` | a mapping for subsystem-specific data (e.g. `live_url`) |

- `ctx.user` → `request.user` or `None`.
- `ctx.child(**overrides)` → a copy with overrides applied; `parent` is reset to
  `None` unless you pass it explicitly. Layout containers call
  `ctx.child(parent=self)` when rendering their children.
- `ctx.resolve(name)` → the value bound to an injectable closure parameter (see
  *Closures* below).

Because the context is frozen, you never mutate it — you derive a new one with
`child()`.

## The fluent / kwargs duality

Every builder accepts configuration two equivalent ways:

```python
TextInput.make("email").label("Email").required()
TextInput("email", label="Email", required=True)   # identical
```

A method decorated `@setter` (`core/component.py:40-43`) is marked
`__dcc_setter__ = True`. The constructor (`_apply_kwargs`, `core/component.py:67-77`)
routes each kwarg to the matching `@setter` method; **a kwarg with no matching
`@setter` raises `TypeError`** listing the valid setter names.

Consequences you must know:

- A plain method that is **not** `@setter` cannot be passed as a kwarg. These are
  fluent-only: `column_span_full()`, `visible_when(...)`, `when(...)`,
  `hidden_when(...)`, `Schema.schema()` / `Schema.form()` / `Schema.model()`,
  `HasChildComponents.schema()` (so `Section(schema=[...])` raises — call
  `.schema([...])`).
- `Column`, `Filter`, `Action`, `Widget` each re-implement the same
  unknown-setter `TypeError` check; the message wording varies slightly.

## `UNSET` vs `None`

`UNSET` (`core/component.py:16-37`) is a falsy singleton meaning *"the caller said
nothing — inherit the default or the bound Django field."* `None` is a real
configured value meaning *"render nothing here"* (e.g. `.label(None)` suppresses a
label that would otherwise be inherited from the form field). Setters store what
you pass; resolution falls back to the Django field only when the value is
`UNSET`.

## `AttributeBag`

Accumulates HTML attributes and renders them escaped (`core/attributes.py:13-75`).

- **`class` is the only attribute that merges** — a caller-supplied class is
  appended to the component's own classes, deduped, order preserved. Every other
  key is last-write-wins.
- Setting a value of `None` or `False` drops the attribute (you cannot force
  `foo="False"`). Boolean attributes (`required disabled checked readonly
  multiple selected autofocus hidden`) render bare (`disabled`) when truthy,
  omitted when falsy.
- `set(key, value)` **raises `ValueError`** if the key is empty or contains
  whitespace or any of `" ' > / =`.
- htmx attribute bags are `AttributeBag`s — `Button.attributes(bag)` merges an
  `htmx.get(...)` result straight in.

## Closures — configuration values that are callables

Almost every setter accepts a callable instead of a literal: `.label(fn)`,
`.visible(fn)`, `.state(fn)`, `Action.action(fn)`, `Table.record_url(fn)`, a
widget's `.value(fn)`, and so on. When the value is rendered, `evaluate()`
(`core/evaluate.py:57-76`) runs it:

1. **Non-callables and classes pass straight through** — a class is *not*
   instantiated. Passing `SomeClass` where you meant `SomeClass()` silently
   returns the class.
2. A callable is inspected for its parameter names and invoked with **only the
   parameters it declares, by name**, drawn from this set
   (`core/evaluate.py:13-26`):

   | name | value |
   |---|---|
   | `record` | `ctx.record` |
   | `request` | `ctx.request` |
   | `user` | `ctx.user` |
   | `form` | `ctx.form` |
   | `operation` | `ctx.operation` |
   | `context` | the `RenderContext` itself |
   | `component` | the component being rendered |
   | `get` / `state` | `get("other_field")` → the current bound value of a sibling form field |
   | `set` | a no-op on the server render path (there is no live state to write back) |

3. A callable that declares **any other parameter name** raises
   `ClosureInjectionError` (a `DCCError`) at render time — including a typo like
   `reqeust`.

So `lambda record: reverse("edit", args=[record.pk])` and
`lambda r, user: ...` (no — `r` is not injectable; use `request`) — declare the
exact injectable names.

See [callbacks.md](callbacks.md) for every call site and its specific contract.

## Safe attribute traversal

Dotted names like `"author.name"` (columns, infolist entries) are walked with
`getattr` by `core/paths.py::traverse`. Because a **stored studio spec** is
user-editable data, the walk refuses:

- any segment starting with `_` (`_meta`, dunders) → renders empty;
- any callable Django flagged `alters_data` (`delete`, `save`) → renders empty,
  never invoked.

A callable attribute that is safe is called with no arguments; a `TypeError`
(it needed arguments) resolves to empty. This mirrors the Django template
language's own `alters_data` guard.

## String-keyed registries

Three registries map a **name** to a **type or owner**, so the request path never
takes an import path from the client:

| Registry | Keys | Consumed by |
|---|---|---|
| `schemas.FIELD_TYPES`, `tables.COLUMN_TYPES` / `FILTER_TYPES`, `infolists.ENTRY_TYPES`, `panels.WIDGET_TYPES` (`core/type_registry.py`) | `"TextColumn"`, `"Toggle"`, … | studio spec deserialisation |
| `actions.registry` (`actions/registry.py`) | an owner key (`"table-articles"`) + an action name | `ActionView` |
| `schemas.endpoints._SCHEMAS` (`register_schema`) | a schema key | `SchemaValidateView` (live field validation) |

`registry.get("Nope")` raises `KeyError` listing what *is* registered; the
endpoints turn a miss into `Http404`.

## Template tags

`{% load dcc_tags %}` (`templatetags/dcc_tags.py`):

| Tag | Purpose |
|---|---|
| `{% dcc_assets alpine=True htmx=True icons=True focus=True %}` | Emit `dcc.css`, the icon-set `<link>`, htmx, `dcc.js`, the Alpine focus plugin, and Alpine — in that order. Pass `False` for anything the host page already loads. |
| `{% dcc_render component %}` | Render a Python component instance; wires `request` and `form` from the template context into a fresh `RenderContext`. |
| `{% dcc_form schema %}` / `{% dcc_form schema form=other_form %}` | Render a bound schema as a full `<form>` including CSRF and a submit button. |
| `{% dcc_icon "rocket" css_class="text-lg" %}` | Render one icon through the active icon set. |
| `{% dcc_studio_assets %}` | The no-code studio builder's CSS + JS. Emit inside a page that already ran `{% dcc_assets %}`. |
| `{% get_field_errors form "name" %}` | **Deprecated** — emits `DeprecationWarning`, removed next minor. The forms bridge renders field errors itself. |

**Load order is load-bearing** (`dcc_tags.py:43-50`): `dcc.js` must load before
Alpine so it can register its `alpine:init` listener before Alpine scans the DOM;
the `@alpinejs/focus` plugin must load before Alpine core (modals/drawers use
`x-trap`). If you pass `alpine=False` / `htmx=False` you own that ordering.

## Design invariants

Four rules are enforced by `tests/test_invariants.py`. They explain many API
shapes:

1. **No literal `hx-*` in any template.** Every htmx attribute comes from
   `htmx.py`. → why views hand templates a pre-built `{{ …_htmx }}` bag.
2. **No hand-rolled `class="dcc-btn"` outside the `ui` layer.** Every button is a
   `ui.Button` (or the `<c-dcc.button>` cotton component). → why tables, actions,
   wizards compose `ui` primitives instead of writing `<button>`.
3. **No `{{ }}` inside `x-data="{…}"`** except a single-argument `dcc*` factory
   call. → why `Menu.items(...)` and `Modal.body(...)` take **pre-rendered HTML
   strings**, and why a custom widget's `x-data` is `myWidget('{{ payload_id }}')`
   and nothing else.
4. **`mark_safe(` is allowed in exactly six files** (`core/attributes.py`,
   `templatetags/dcc_tags.py`, `schemas/schema.py`, `schemas/layout.py`,
   `tables/columns.py`, `icons/fontawesome.py`). Everywhere else output is
   escaped through `format_html`. → why `.allow_html()` on a column is an
   explicit, documented opt-out and the only way to emit computed markup.

## Where to go next

- [settings.md](settings.md) — every `DCC[...]` key, install, system checks.
- [views-and-mixins.md](views-and-mixins.md) — every view and mixin, MRO rules.
- [callbacks.md](callbacks.md) — every user-supplied callable and its contract.
- [errors.md](errors.md) — every exception and what triggers it.
