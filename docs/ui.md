# UI primitives

One Python component + one leaf template per primitive. Every other subsystem
(tables, actions, wizards, panels) composes these instead of hand-writing
`<button>` / `<span class="dcc-badge">` markup, so a restyle or an htmx-version
bump happens in one place.

```python
from django_cotton_components.ui import Button, Badge, Icon, Checkbox, Menu, Modal
from django_cotton_components.core.context import RenderContext

ctx = RenderContext(request=request)
html = Button.make().label("Save").variant("primary").type("submit").render(ctx)
```

Render a component in a template with `{% dcc_render component %}`.

## Button

`Button.make()` → `<button>`, or `<a>` when `.href(...)` is set.

| setter | |
|---|---|
| `.label(str)` | |
| `.icon(name)` | FontAwesome icon, left of the label |
| `.variant(str)` | `primary`, `secondary` (default), `danger`, `ghost`, `link` |
| `.size(str)` | e.g. `sm` |
| `.href(url)` | render as a link |
| `.type(str)` | `button` (default), `submit`, `reset` |
| `.disabled()` | |
| `.attributes(bag \| dict)` | merge extra attrs — htmx `AttributeBag`, Alpine handlers, … |

`IconButton` is a `Button` whose visible content is only the icon; `label`
becomes the `aria-label`.

## Badge

`Badge.make().label("Live").variant("success").icon("circle")` → a pill.

## Icon

`Icon.make("rocket").css_class("text-lg")` renders through the active icon set
(`DCC["ICON_SET"]`, default FontAwesome). Shortcut tag: `{% dcc_icon "rocket" %}`.

## Checkbox

`Checkbox.make().label("Featured").value("on").checked().attributes({...})` — a
standalone labelled checkbox (the table selection column and schema `Checkbox`
field are separate).

## Menu

An Alpine disclosure: a trigger button (default "⋯") and a list of **pre-rendered
HTML item strings**.

```python
Menu.make().icon("ellipsis-vertical").align("end").items([
    action_a.render_trigger(record=obj, request=request),
    action_b.render_trigger(record=obj, request=request),
])
```

Opens on click, closes on Escape / click-outside. Used by table row actions
marked `.collapsed()`.

## Modal

A teleported overlay with a focus trap. The body is **pre-rendered HTML**
(`.body(...)`) because the Python render path has no slot mechanism.

```python
Modal.make().heading("Confirm").size("sm").body(form_html).render(ctx)
```

`open_on_load` (default true) starts it visible — the action endpoint swaps a
ready-open modal into a table's `#dcc-modal-<owner>` mount. Close it by swapping
the mount empty (what a successful modal action does) or dispatching the
`dcc-modal-close` window event.

## Icon set

```python
DCC = {
    "ICON_SET": "django_cotton_components.icons.FontAwesome",
    "ICON_ASSET_URL": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.7.2/css/all.min.css",
}
```
Set `ICON_ASSET_URL` to `None` if the set self-hosts. Implement `IconSet` to
swap in a different library.
