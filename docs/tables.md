# Tables

`Table.make(queryset)` builds a data table from a fluent chain. It renders
itself, picks client- or server-side mode by row count, and answers its own
htmx requests.

```python
from django_cotton_components.tables import (
    Table, TextColumn, DateColumn, BooleanColumn, SelectFilter, TernaryFilter,
)
from django_cotton_components.actions import Action, BulkAction

def article_table(request):
    return (
        Table.make(Article.objects.select_related("author"))
        .id("articles")
        .columns([
            TextColumn.make("title").sortable().searchable().limit(64),
            TextColumn.make("author.name").label("Author").sortable(sort_field="author__name"),
            BooleanColumn.make("featured").labels(("★", "—")),
            DateColumn.make("created_at").label("Created").since().sortable(),
        ])
        .filters([
            SelectFilter.make("status").options(Article.Status.choices),
            TernaryFilter.make("featured"),
        ])
        .actions([
            Action.make("edit").icon("pen").to_url(lambda r: f"/articles/{r.pk}/edit/"),
            Action.make("quick_edit").icon("pen-to-square").modal(quick_edit_schema()),
        ])
        .bulk_actions([
            BulkAction.make("publish").icon("rocket").requires_confirmation()
            .action(lambda records: records.update(status="live")),
        ])
        .searchable()
        .default_sort("-created_at")
    )
```

Render it from a view with `TableMixin`:

```python
class ArticleListView(TableMixin, TemplateView):
    template_name = "articles/list.html"
    def get_table(self):
        return article_table(self.request)
```

```django
{{ table_html }}
```

`TableMixin` also serves the fragment: an `HX-Request` carrying `?_dcc_table=<id>`
returns just the table body, so filters, sort, search, pagination and scroll all
swap in place.

## Columns

| column | notes |
|---|---|
| `TextColumn` | `.limit(n)` truncates; `.state(fn)` overrides the value (`lambda record: ...`); `.allow_html()` opts a computed cell out of escaping |
| `BooleanColumn` | `.labels(("yes", "no"))` |
| `BadgeColumn` | `.colors({value: variant})` |
| `DateColumn` | `.since()` → "3 days ago", else `.date_format("N j, Y")` |
| `ImageColumn` | `.thumbnail((48, 48))`, `.rounded()` |

Every column takes `.label(...)`, `.sortable(sort_field=...)`, `.searchable([paths])`.
Query-string values never reach the ORM as keys — a requested sort must name a
column that declared itself sortable.

## Filters

`SelectFilter.make("status").options([...])`, `BooleanFilter`, `TernaryFilter`
(All / Yes / No). Filters round-trip to the server on `change` in both modes;
a value that doesn't clean is ignored, never a 500.

## Client vs server mode

- **≤ `DCC["TABLE_CLIENT_SIDE_MAX_ROWS"]` rows (default 200):** client mode —
  every row is rendered once, and Alpine filters/sorts/paginates in the DOM with
  **zero background requests**. Rich cells and row actions keep working.
- **More:** server mode. Force either with `.client_side()` / `.server_side()`.

## Large datasets

Server mode defaults to `.stream()` — **keyset (cursor) pagination**: order by
`(sort_column, pk)`, ask for "the page after this row", fetch `per_page + 1` to
know if more exist. **No `COUNT(*)`, no `OFFSET`.** A sentinel row at the bottom
carries `hx-trigger="revealed"` and appends the next batch (infinite scroll);
`.load_more_button()` makes it a click instead.

`.page_numbers()` opts back into classic numbered pages (one `COUNT(*)` per
render) — fine for small server-side sets.

### Bulk actions over millions of rows

Tick the header checkbox, then "Select every matching row". The bulk action then
receives the **filtered queryset itself** (not a pk list), so the callback can
`records.update(...)` in a single query.

## Row actions

- `.to_url(fn)` — render as a link, navigate to a page.
- `.modal(schema)` — open that schema's form in a modal, bound to the row's record.
- `.modal()` / `.requires_confirmation()` — a confirm dialog.
- `.action(fn)` alone — `hx-post`, swap the row, fire a toast + refresh.

`.action(fn)` params are injected by name: `request`, `user`, `record` (row) /
`records` (bulk), `data` (a `.schema(...)` form's cleaned data).
