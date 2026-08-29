# UI primitives

## Mental model

One Python component + one leaf template per primitive. Every other subsystem
(tables, actions, wizards, panels) composes these instead of hand-writing
`<button>` / `<span class="dcc-badge">` markup — so a restyle or an htmx-version
bump happens in one place. A lint test forbids a hand-rolled `class="dcc-btn"`
anywhere outside this layer.

There are **two** ways to use each primitive:

- **The Python class** (`django_cotton_components.ui`) — for code that builds HTML
  (a table cell, an action trigger).
- **The `<c-dcc.*>` cotton component** (`templates/cotton/dcc/*.html`) — for
  template authors. These are a *separate, smaller* implementation with a
  `{{ slot }}` and a self-contained trigger where relevant.

```python
from django_cotton_components.ui import Button, Badge, Icon, Checkbox, Menu, Modal
from django_cotton_components.core.context import RenderContext

ctx = RenderContext(request=request)
html = Button.make().label("Save").variant("primary").type("submit").render(ctx)
```

Render a Python component in a template with `{% dcc_render component %}`.

## Button (Python)

`Button.make()` → `<button>`, or `<a>` when `.href(...)` is set.

| setter | note |
|---|---|
| `.label(str)` | `None` or `False` both render as empty |
| `.icon(name)` | icon left of the label |
| `.variant(str)` | `primary`, `secondary` (default), `danger`, `ghost`, `link`. **An unknown value warns and falls back to `secondary`.** |
| `.size(str)` | any token → `dcc-btn--<token>` class; only `sm` is styled |
| `.href(url)` | render as `<a>` |
| `.type(str)` | `button` (default), `submit`, `reset` |
| `.disabled()` | |
| `.attributes(bag \| dict)` | merge extra attrs — an htmx `AttributeBag`, Alpine handlers. Repeated calls accumulate. Merged *after* the styling classes so `{{ attrs }}` carries both. |

`IconButton` is a `Button` whose visible content is only the icon; `label`
becomes the `aria-label` and the visible label span is blank. Same setters.

## Badge (Python)

`Badge.make().label("Live").variant("success").icon("circle")` → a pill.

`variant` accepts **any** string → `dcc-badge--<variant>`; the actual set of
styled variants is defined in `css/dcc.css` (`success`, `danger`, `muted`, …) —
an unknown one just yields an unstyled class. `label` is auto-escaped.

## Icon (Python)

`Icon.make("rocket").css_class("text-lg")` renders through the active icon set.
The name is the **positional** argument. Only setter: `.css_class(str)`. Shortcut
tag: `{% dcc_icon "rocket" %}`.

An invalid name (uppercase, dots, slashes, `../`) renders an **empty string
silently** — there is no error for a typo.

## Checkbox (Python)

`Checkbox.make().label("Featured").value("on").checked().attributes({...})` — a
standalone labelled checkbox. `input_name` comes from the component `name`. The
table selection column and the schema `Checkbox` field are separate
implementations.

## Menu (Python)

An Alpine disclosure: a trigger button (default icon `ellipsis-vertical`) and a
list of **pre-rendered HTML item strings**.

```python
Menu.make().icon("ellipsis-vertical").align("end").items([
    edit_action.render_trigger(record=obj, request=request),
    delete_action.render_trigger(record=obj, request=request),
])
```

| setter | note |
|---|---|
| `.label(str)` | trigger text |
| `.icon(name)` | trigger icon (default `ellipsis-vertical`) |
| `.items([str, …])` | **pre-rendered HTML** — there is no slot |
| `.align("start" \| "end")` | menu alignment (default `end`) |

Opens on click, closes on Escape / click-outside. Used by table row actions
marked `.collapsed()`.

**Why pre-rendered HTML:** a lint test forbids `{{ }}` inside `x-data="{…}"`, so
the Python render path cannot hand a template into the Alpine component — the
items must already be strings.

## Modal (Python)

A teleported overlay with a focus trap (`x-trap.inert.noscroll`). The body is
**pre-rendered HTML** (`.body(...)`) for the same reason as `Menu`.

```python
Modal.make().heading("Confirm").size("sm").body(form_html).render(ctx)
```

| setter | note |
|---|---|
| `.heading(str)` | header text and `aria-label`; header block only renders when set |
| `.size(str)` | any token → `dcc-modal__dialog--<token>` |
| `.body(str \| SafeString)` | rendered with `\|safe` — **the caller owns escaping** |
| `.open_on_load(value=True)` | data flag (default `True`); the action endpoint swaps a ready-open modal into a table's `#dcc-modal-<owner>` mount |
| `.dom_id(str)` | an id for the wrapper |

Close it by swapping the mount empty (what a successful modal action does) or
dispatching the `dcc-modal-close` window event.

The `x-trap` focus containment needs the `@alpinejs/focus` plugin —
`{% dcc_assets %}` emits it before Alpine core. Pass `focus=False` only if the
host page already loads it.

## `<c-dcc.*>` cotton components (templates)

For template authors. Load with `{% load cotton %}` (or add cotton to
`builtins`).

### `<c-dcc.button>`

```django
<c-dcc.button variant="primary" label="Save" type="submit" />
<c-dcc.button href="/x/" icon="pen" label="Edit" />
<c-dcc.button variant="danger">Delete<c-dcc.button>   {# slot content #}
```

`<c-vars>`: `variant="secondary"`, `type="button"`, `href=""`, `icon=""`,
`label=""`, `size=""`. Merges the caller's `{{ class }}` and `{{ attrs }}`.
Renders `<a>` when `href` is set. Supports `{{ slot }}` in addition to `label`.

### `<c-dcc.badge>`

```django
<c-dcc.badge label="Live" variant="success" />
```

`<c-vars>`: `label=""`, `variant=""`. Supports `{{ slot }}`.

### `<c-dcc.modal>`

```django
<c-dcc.modal id="publish" header="Publish?" trigger_label="Publish" trigger_variant="primary">
  <p>This makes the article public.<p>
<c-dcc.modal>
```

`<c-vars>`: `id="dcc-modal"`, `header=""`, `trigger_label="Open"`,
`trigger_variant="primary"`. **Self-contained** — it renders its own trigger
button, teleports to `<body>`, and traps focus. The body is `{{ slot }}`. Use
this one for author-controlled modals; the Python `Modal` is for endpoint-driven
ones.

There is no `<c-dcc.menu>` or `<c-dcc.icon>` component — use `{% dcc_icon %}` and
the Python `Menu`.

## Icon set

```python
DCC = {
    "ICON_SET": "django_cotton_components.icons.FontAwesome",
    "ICON_ASSET_URL": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.7.2/css/all.min.css",
}
```

`ICON_ASSET_URL = None` → the set self-hosts / emits nothing.

### Implementing a set

Satisfy the `IconSet` protocol (`icons/base.py:15-23`):

```python
class MyIcons:
    def __init__(self, asset_url=None):        # optional — see note below
        self.asset_url = asset_url

    def render(self, name, *, css_class=""):    # -> SafeString (already safe)
        ...

    def assets(self):                           # -> SafeString of <link>/<script>
        ...
```

- The registry memoises the resolved set with `@lru_cache(maxsize=1)`, keyed on
  `(dotted_path, asset_url)`. It is cleared only when the `DCC` setting itself
  changes (a `setting_changed` receiver — so `override_settings(DCC=...)` in
  tests works).
- The registry calls `cls(asset_url=...)` and, on `TypeError`, retries `cls()` —
  so your set may take the `asset_url` kwarg or not.

### FontAwesome (default)

- Name grammar: `"<style>:<icon>"` or bare `"<icon>"` (default style `solid`).
  Styles: `solid regular light thin duotone brands`. An unrecognised style is
  treated as part of the icon name.
- Icon tokens must match `[a-z0-9-]+`. Anything else → `render()` returns `""`.

## Constraints / do not combine

- `Menu.items(...)` and `Modal.body(...)` are HTML strings, not templates — you
  cannot pass a component; render it first (`component.render(ctx)`).
- `Modal.open_on_load` only sets a data flag; the template's visibility is driven
  by the endpoint that swaps the modal in. For an author-controlled modal use
  `<c-dcc.modal>`.
- `Button.variant()` never raises — it warns and coerces. Watch your dev console.
- `Icon` / `{% dcc_icon %}` never raise on a bad name — they render nothing.

## Known sharp edges

- The two button implementations differ: the Python `Button.variant()` warns and
  coerces; the `<c-dcc.button>` template interpolates `{{ variant }}` verbatim
  into the class (no validation).
- `<c-dcc.modal>` renders its own trigger; the Python `Modal` does not. Do not
  mix the two for one dialog.
