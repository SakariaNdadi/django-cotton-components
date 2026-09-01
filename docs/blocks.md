# Blocks

`django_control_components.blocks` — page and layout building blocks. Where a
form's `Section` / `Fieldset` / `Tabs` (in `schemas/`) render inside a bound
Django form, these are the **page-level** equivalents: a component with *named
child slots*, rendered through the ordinary `template_name` path, registered in
`BLOCK_TYPES` so the studio palette offers them.

The layout/chrome blocks are the visible half of the "sidebars, navbars,
footers, placing them" story; the tree-builder UI that edits them arrives with
`Page` (see [no-code.md](no-code.md)).

## `Block`

`Block(Component)` adds one thing over `Component`: `slots: tuple[str, ...]`.

```python
from django_control_components.blocks import Card, Grid, Column

Grid.make().cols(12).fill(
    "default",
    [
        Column.make().span(8).fill("default", [main_content]),
        Column.make()
        .span(4)
        .fill(
            "default",
            [
                Card.make().title("Summary").fill("body", [summary]),
            ],
        ),
    ],
)
```

- `.fill(slot, [children])` — set a named slot's children. Raises on an unknown
  slot or a non-`Block` child.
- `.slot_children(slot)` / `.render_slot(slot, ctx)` — read / render one slot.
- `get_view_data(ctx)["slots"]` is `{slot_name: rendered_html}` for the template.

Everything else — `@setter` config, `.visible()` / `.hidden()`, `.make()` — is
the standard `Component` contract.

## Layout blocks (`blocks/layout.py`)

| Block | Slots | Setters |
|---|---|---|
| `Stack` | `default` | `.gap(none/sm/md/lg/xl)`, `.align(...)` — vertical flow |
| `Row` | `default` | `.gap`, `.align`, `.justify(start/center/end/between/around)`, `.wrap(bool)` |
| `Grid` | `default` | `.cols(int=12)`, `.gap` |
| `Column` | `default` | `.span(int)`, `.offset(int)` — a `Grid` child |
| `Card` | `header` `body` `footer` | `.title(str)` |
| `Divider` | — | — |
| `Spacer` | — | `.size(none/sm/md/lg/xl)` |

## Chrome blocks (`blocks/chrome.py`)

| Block | Slots | Setters |
|---|---|---|
| `AppShell` | `topbar` `sidebar` `content` `footer` | `.sidebar_width(str)` — the page frame; reuses `.dcc-panel` + `dccShell()` |
| `Navbar` | `start` `end` | `.brand(str)` |
| `Sidebar` | `default` | `.brand(str)`, `.brand_icon(str)` |
| `Footer` | `default` | — |

`AppShell` only emits the mobile nav-toggle + scrim when its `sidebar` slot is
filled, and only wraps a `topbar` / `footer` when those slots are non-empty — a
shell with just `content` renders a bare `<main>`.

## `BLOCK_TYPES`

The sixth `TypeRegistry`, alongside `FIELD_TYPES` / `COLUMN_TYPES` /
`FILTER_TYPES` / `ENTRY_TYPES` / `WIDGET_TYPES`. Every block above is registered
`category="block"`; `studio/palette.py` dumps it under `palette()["blocks"]`,
and `strip_privileged_setters` applies. A downstream project registers a custom
block the same way: `BLOCK_TYPES.register(MyBlock, label=…, icon=…, category="block")`.

## The node codec (`blocks/codec.py`)

`encode_nodes` / `decode_node` / `decode_nodes` are the single wire↔stored
transform for a flat `{type, name, config}` node list — the builder JS edits
`{id, type, config}` with `name` folded into `config.name`; storage keeps them
separate. The dashboard and resource builders both use it.

## Spec migrations (`studio/specmigrations/`)

When the stored document shape changes across releases, a migration upgrades an
old row on **read** — it keeps resolving under the version it was written with,
and is rewritten lazily on next save.

```python
from django_control_components.studio.specmigrations import register


@register(2, "grid_cols_default")
def forward(doc):
    ...
    return doc
```

`migrate(doc)` applies every step whose `version` exceeds the document's own
`schema_version`, in ascending order, never mutating the input. The production
registry is empty until a stored field adopts the `{"schema_version": n,
"root": {...}}` envelope.
