# Infolists

An **Infolist** is the read-only counterpart to a `Schema`: it renders a record
as labelled values, with no form and no inputs. Panels use it for the view page;
you can render one anywhere.

```python
from django_cotton_components.infolists import (
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

With no `.schema([...])`, `Infolist.make().model(Article)` renders one
`TextEntry` per model field.

## Entries

| entry | renders |
|---|---|
| `TextEntry` | the value, escaped; `—` (or `.placeholder(...)`) when empty |
| `BadgeEntry` | a `<c-dcc.badge>`; `.colors({value: variant})` maps the raw value to a variant |
| `BooleanEntry` | `Yes` / `No` badge |
| `DateEntry` | `.since()` → "3 days ago"; else `.date_format("N j, Y")` |

Every entry takes `.label(...)`, `.placeholder(...)` and `.state(fn)` (a closure
`lambda record: ...` that overrides the value). Dotted names (`"author.name"`)
walk relations. Layout with `Section` / `Grid` from
`django_cotton_components.schemas` works the same as in a schema.

## In a panel

```python
class ArticleResource(Resource):
    model = Article

    @classmethod
    def build_infolist(cls, *, request):
        return Infolist.make().schema([...])
```
