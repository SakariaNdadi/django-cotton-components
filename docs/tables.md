# Tables

`Table.make(queryset)` builds a data table from a fluent chain. It renders
itself, picks client- or server-side mode by row count, and answers its own
htmx requests.

```python
from django.urls import reverse
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
            Action.make("edit").icon("pen").to_url(lambda r: reverse("article-edit", args=[r.pk])),
            Action.make("quick_edit").icon("pen-to-square").collapsed()
                .modal(quick_edit_schema()).action(save_quick_edit),
        ])
        .bulk_actions([
            BulkAction.make("publish").icon("rocket").requires_confirmation()
                .action(lambda records: records.update(status="live")),
        ])
        .searchable()
        .default_sort("-created_at")
        .record_url(lambda r: reverse("article-edit", args=[r.pk]))
        .record_preview(lambda r: format_html("<strong>{}</strong><p>{}</p>", r.title, r.body[:200]))
    )
```

Render it from a view with `TableMixin`:

```python
from django_cotton_components.tables.views import TableMixin

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
swap in place. In a panel `Resource` the table comes from `build_table()` — see
[panels.md](panels.md).

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
column that declared itself sortable, and the ORM path comes from the column's
declared `sort_field` / `searchable` list.

## Filters

`SelectFilter.make("status").options([...])`, `BooleanFilter`, `TernaryFilter`
(All / Yes / No). Filters round-trip to the server on `change` in both modes;
a value that doesn't clean is ignored, never a 500.

## Client vs server mode

- **≤ `DCC["TABLE_CLIENT_SIDE_MAX_ROWS"]` rows (default 200):** client mode —
  every row is rendered once, and Alpine filters/sorts/paginates in the DOM with
  **zero background requests**. Rich cells, row actions and selection keep working.
- **More:** server mode. Force either with `.client_side()` / `.server_side()`.

## Pagination

| call | effect |
|---|---|
| *(nothing)* | fixed page size of 10, no size picker |
| `.paginate([10, 25, 50])` | page size 10; a **"Rows"** `<select>` lets the user switch. First value is the default |
| `.pagination_position("left" \| "center" \| "right")` | where the pager sits (default `right`) |
| `.page_numbers()` | classic numbered pages — one `COUNT(*)` per render, fine for small server-side sets |
| `.infinite_scroll()` | no pager; rows append on scroll (server: keyset cursor + `hx-trigger="revealed"`; client: an `IntersectionObserver` sentinel) |
| `.load_more_button()` | with the streaming strategy, a click instead of auto-append |

The grid width is fixed (100% of its container); its height follows the number
of rows on the page.

## Large datasets

Server mode defaults to **keyset (cursor) pagination**: order by
`(sort_column, pk)`, ask for "the page after this row", fetch `per_page + 1` to
know if more exist. **No `COUNT(*)`, no `OFFSET`.** A sentinel row at the bottom
carries `hx-trigger="revealed"` and appends the next batch.

## Row selection & bulk actions

`.bulk_actions([...])` adds a leading checkbox column and a toolbar that slides
in once rows are ticked. Selecting rows survives a client-mode filter round-trip.

Tick the header checkbox, then **"Select every matching row"**: the bulk action
receives the **filtered queryset itself** (not a pk list), so the callback can
`records.update(...)` in a single query over millions of rows.

```python
BulkAction.make("archive").requires_confirmation()
    .action(lambda records: records.update(status="archived"))
```

## Row actions

`.actions([...])` renders one button per action in a trailing column.

- `.to_url(fn)` — a link, navigates to a page.
- `.modal(schema)` — opens that schema's form in a modal, bound to the row's record; `.action(fn)` saves it.
- `.modal(fn)` — renders `fn(record=...)` HTML in a modal.
- `.modal()` / `.requires_confirmation()` — a confirm dialog.
- `.action(fn)` alone — `hx-post`, then a toast + table refresh.
- `.collapsed()` — fold this action into a trailing **"⋯" menu** instead of showing it inline.
- `.icon(name)`, `.variant("secondary" | "danger" | …)`, `.visible(fn)`, `.authorize("app.perm")`.

`.action(fn)` params are injected by name: `request`, `user`, `record` (row) /
`records` (bulk), `data` (a `.modal(schema)` form's cleaned data). Modal actions
that mutate fire an `HX-Trigger` that closes the dialog, shows a toast and
refreshes the table. See [actions.md](actions.md).

## Whole-row click & hover preview

| call | effect |
|---|---|
| `.record_url(lambda r: url)` | clicking anywhere on a row (bar its buttons/inputs) navigates to that URL (full page); ⌘/Ctrl-click opens a new tab; the row is keyboard-focusable, Enter activates |
| `.record_action(action)` | a row click fires an `Action` instead — typically `.modal(...)` for a detail dialog, or `.to_url(...)` |
| `.record_preview(lambda r: html)` | hovering a row (~350 ms) pops a floating card with the returned HTML |

Clicks on interactive descendants (buttons, links, inputs, the selection
checkbox, the "⋯" menu) never trigger the row action, and text selection is
ignored.

## Presentation

`.presentation("feed")` renders rows as a borderless list instead of a grid —
for compact dashboard cards. The first cell is the title, middle cells the meta
line, the last cell a trailing element (when 3+ columns). Combine with
`.client_side()` for a small always-in-page list.

```python
Table.make(Article.objects.order_by("-created_at")[:6])
    .columns([TextColumn.make("title"), TextColumn.make("author.name"), BadgeColumn.make("status")])
    .client_side().presentation("feed")
```

## Settings

```python
DCC = {
    "TABLE_CLIENT_SIDE_MAX_ROWS": 200,
    "TABLE_PER_PAGE_CHOICES": [10, 25, 50, 100],  # only the first is used unless .paginate() is called
}
```
