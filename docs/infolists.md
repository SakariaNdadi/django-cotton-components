# Infolists

## Mental model

An `Infolist` is the **read-only counterpart to a `Schema`**: it renders a record
as labelled values, with no form and no inputs. Panels use it for the view page;
you can render one anywhere.

Entries are `Component` subclasses, so everything from
[architecture.md](architecture.md) applies — `get_view_data` is the render hook,
`.visible()` / `.hidden()` work, dotted names are walked with the safe
`core.paths.traverse` (a segment starting `_` or a Django `alters_data` method
resolves to empty, never called).

## Quick start

```python
from django_control_components.infolists import (
    Infolist, TextEntry, BadgeEntry, BooleanEntry, DateEntry,
)

infolist = Infolist.make().schema([
    TextEntry.make("title"),
    TextEntry.make("author.name").label("Author"),
    BadgeEntry.make("status").colors({"live": "success", "archived": "muted"}),
    BooleanEntry.make("featured"),
    DateEntry.make("created_at").since(),
])

html = infolist.render(request=request, record=article)
```

## `Infolist`

| Method | Effect |
|---|---|
| `Infolist.make()` | construct |
| `.model(Model)` | with no `.schema(...)`, render one `TextEntry` per model field (label = `verbose_name.title()`) |
| `.schema([...])` / `.components([...])` | the entry / layout tree (aliases; fluent-only) |
| `.render(*, request=None, record=None)` | `SafeString`; builds a `RenderContext(operation="view")` |

`record` can be a model instance, a `dict`, or a `SimpleNamespace`. A wizard
review step passes `get_all_cleaned_data()` (a dict is wrapped automatically by
the wizard — see [wizards.md](wizards.md)).

## Entries

| Entry | Renders | Extra setter |
|---|---|---|
| `TextEntry` | the value; `—` (or `.placeholder(...)`) when `None` / `""` | — |
| `BadgeEntry` | a `dcc-badge` pill; `.colors({raw_value: variant})` maps the value to a variant | `.colors(dict)` |
| `BooleanEntry` | `Yes` / `No` badge (`No` is unstyled, `Yes` is `success`) | — |
| `DateEntry` | `.since()` → "3 days ago"; else `.date_format("N j, Y")` (default) | `.since()`, `.date_format(fmt)` |

Every entry (via `Entry` / `Component`):

| Setter | Note |
|---|---|
| `.label(str)` | default: title-cased name with `_` / `.` → space |
| `.placeholder(str)` | shown when the value is `None` or `""` (default `"—"`) |
| `.state(fn)` | override the value; `lambda record: ...` (closure — injected by name) |
| `.visible(bool\|fn)` / `.hidden(...)` / `.when(...)` | from `Component` |

`.state(fn)` is a closure evaluated through `evaluate()` — declare injectable
parameter names (`record`, `request`, `user`, …); see [callbacks.md](callbacks.md).
Values are **escaped** — there is no `.allow_html()` on an entry.

## Layout

`Section` / `Grid` from `django_control_components.schemas` nest inside
`.schema([...])` exactly as in a form schema.

## In a panel

```python
class ArticleResource(Resource):
    model = Article

    @classmethod
    def build_infolist(cls, *, request):
        return Infolist.make().schema([...])
```

The panel view page calls `build_infolist(request=...).render(request=...,
record=obj)`. See [panels.md](panels.md).

## Constraints

- `Entry(name=None)` is allowed at construction, but an entry with no name and no
  `.state(fn)` resolves to the placeholder — always give a name or a `.state`.
- Base `Entry` is not registered for no-code specs; `TextEntry`, `BadgeEntry`,
  `BooleanEntry`, `DateEntry` are.
- `.state(fn)` output is escaped; there is no HTML opt-out. For computed markup,
  render the infolist yourself and interleave your own safe HTML, or use a
  column in a table.

## Known sharp edges

- `BooleanEntry` treats any falsy `raw_value` (including `None` for a missing
  relation) as `"No"` — it does not distinguish "false" from "unknown".
- `.model(Model)` iterates `model._meta.fields` — reverse relations and
  many-to-many are not included.
