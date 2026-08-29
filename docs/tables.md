# Tables

## Mental model

`Table.make(queryset)` builds a data table from a fluent chain. One object:

- renders its own shell **and** its own content fragment;
- picks **client- or server-side mode** by row count;
- answers its own htmx requests (sort, filter, search, paginate, scroll);
- is an **action owner** — row and bulk actions register against it.

**No querystring value ever reaches the ORM as a key.** A requested sort must
name a column that declared itself `sortable`; the ORM path then comes from that
column's `sort_field()`. Search builds a `Q` over columns that declared
themselves `searchable`, nothing else (`tables/query.py:1-8`). A filter value
that does not clean is dropped — never a 500 (`tables/filters.py:1-6`).

Why keyset pagination in server mode: deep `OFFSET` and `SELECT COUNT(*)` both
scale badly. Server mode orders by `(sort_column, pk)`, asks for "the page after
this row", and fetches `per_page + 1` to know whether more exist — no count, no
offset (`tables/cursor.py:1-10`). The cursor token is an opaque base64 of
`[sort_value, pk]`; it carries no column name, so a tampered token can at worst
point at a wrong row inside the already-scoped queryset.

## Quick start

```python
from django.urls import reverse
from django_control_components.tables import (
    Table, TextColumn, DateColumn, BooleanColumn, SelectFilter, TernaryFilter,
)
from django_control_components.actions import Action, BulkAction

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
            Action.make("edit").icon("pen").to_url(lambda record: reverse("article-edit", args=[record.pk])),
            Action.make("quick_edit").icon("pen-to-square").collapsed()
                .modal(quick_edit_schema()).action(save_quick_edit),
        ])
        .bulk_actions([
            BulkAction.make("publish").icon("rocket").requires_confirmation()
                .action(lambda records: records.update(status="live")),
        ])
        .searchable()
        .default_sort("-created_at")
        .record_url(lambda record: reverse("article-edit", args=[record.pk]))
        .record_preview(lambda record: format_html("<strong>{}</strong><p>{}</p>", record.title, record.body[:200]))
    )
```

Render it from a view with `TableMixin`:

```python
from django_control_components.tables.views import TableMixin

class ArticleListView(TableMixin, TemplateView):
    template_name = "articles/list.html"
    def get_table(self):
        return article_table(self.request)
```

```django
{{ table_html }}
```

## `Table` — configuration

All methods are **fluent-only** and return `self`. (They are not `@setter`s —
`Table` has no kwargs constructor.)

| Method | Effect |
|---|---|
| `.id(str)` | stable id; the `?_dcc_table=<id>` fragment handle. Defaults to the model name. |
| `.columns([...])` | the column list |
| `.filters([...])` | the filter list |
| `.actions([...])` | row actions (one button per action in a trailing column) |
| `.bulk_actions([...])` | bulk actions (leading checkbox column + a toolbar) |
| `.searchable(value=True)` | show a search box (auto-on if any column is `.searchable()`) |
| `.default_sort("field" \| "-field")` | initial sort; `-` prefix = descending |
| `.paginate([10, 25, 50])` | page size = first value; a "Rows" `<select>` offers the rest |
| `.pagination_position("left" \| "center" \| "right")` | pager placement (default `right`) |
| `.page_numbers()` | classic numbered pages — one `COUNT(*)` per render |
| `.stream()` | keyset cursor + append-on-scroll; safe over millions of rows |
| `.infinite_scroll()` | no pager; rows append on scroll |
| `.load_more_button()` | with streaming, a click instead of auto-append |
| `.client_side()` / `.server_side(*, strategy=None)` | force the mode |
| `.presentation("grid" \| "feed")` | `feed` = borderless list for dashboard cards |
| `.empty_message(str)` | text when there are no rows |
| `.record_url(fn)` | whole-row click navigates to `fn(record)` (full page) |
| `.record_action(action)` | whole-row click fires an `Action` instead |
| `.record_preview(fn)` | hovering a row (~350 ms) pops a card with `fn(record)` HTML |

### Client vs server mode

- **≤ `DCC["TABLE_CLIENT_SIDE_MAX_ROWS"]` rows (default 200):** client mode. Every
  row is rendered once; Alpine filters/sorts/paginates in the DOM with **zero
  background requests**. Rich cells, row actions and selection keep working.
- **More:** server mode.
- Mode is auto-probed with `queryset.values_list("pk")[:max+1]` unless you call
  `.client_side()` / `.server_side()`, which disable the probe.

### Pagination strategy interactions

- `.infinite_scroll()` **forces** the streaming strategy — it overrides
  `.page_numbers()` and `.stream()` (`tables/table.py:137-140`).
- The "rows per page" `<select>` renders **only** when you passed **more than one**
  choice to `.paginate([...])` **and** the table is in server mode
  (`tables/table.py:334-338`). Otherwise the first choice is a fixed page size
  (10 by default).
- `.page_numbers()` (`"pages"` strategy) is the only path that runs `COUNT(*)`.
  Fine for small server-side sets; avoid for large ones.

## Columns

Import from `django_control_components.tables`.

| Column | `format` behaviour / extra setters |
|---|---|
| `TextColumn` | the value, escaped |
| `BooleanColumn` | `.labels(("yes", "no"))` → a `dcc-badge` pill; default `("Yes", "No")` |
| `BadgeColumn` | `.colors({value: variant})` → a `dcc-badge` pill |
| `DateColumn` | `.since()` → "3 days ago"; else `.date_format("N j, Y")` |
| `ImageColumn` | `.thumbnail((48, 48))`, `.rounded()` → an `<img>`; thumbnail derivation failures fall back to the original URL silently |

### Every column setter

`Column.make(name, **kwargs)` — `name` may be dotted (`"author.name"`), walked
safely (see [architecture.md](architecture.md#safe-attribute-traversal)).

| Setter | Note |
|---|---|
| `.label(str)` | header text; default is the title-cased name |
| `.sortable(sort_field="orm__path" \| True)` | declares the column sortable; the value is the ORM path (default: name with `.`→`__`) |
| `.searchable(["orm__path", …] \| True)` | declares the column searchable; the list is the ORM paths (default: `[name.replace(".", "__")]`) |
| `.align(str)` | cell alignment |
| `.limit(n)` | truncate the display text to `n` chars with `…` |
| `.allow_html()` | opt a computed cell **out of escaping** (`mark_safe`). The only sanctioned way to emit markup; pair with `.state(fn)` returning `format_html(...)` |
| `.state(fn)` | override the displayed value; `lambda record: ...` |

`.state(fn)` without `.allow_html()` renders the returned string **escaped** —
so `format_html("<b>{}</b>", x)` shows the literal tags. Add `.allow_html()`.

Query-string values never reach `order_by` / `filter` as keys — a requested sort
must name a `sortable` column; a search only touches `searchable` columns.

## Filters

`SelectFilter.make("status").options([...])`, `BooleanFilter`, `TernaryFilter`
(All / Yes / No), and the base `Filter` (a text `icontains` match).

| Filter | Behaviour |
|---|---|
| `Filter` | `form_field = CharField(required=False)`; `queryset.filter(Q(**{orm_field: value}))` |
| `SelectFilter` | `.options(pairs \| dict)`; a value not in the option set is ignored |
| `BooleanFilter` | `"true"`→`True`, `"false"`→`False`, anything else ignored |
| `TernaryFilter` | `BooleanFilter` with All / Yes / No choices |

Setters: `.label(str)`, `.field("orm__path")` (the ORM field, default = name).
Filters round-trip to the server on `change` in **both** modes — client-side
value/display equality is unreliable, especially for booleans
(`tables/table.py:467-469`). A garbage value is dropped, never a 500.

## Row actions

`.actions([...])` renders one button per action in a trailing column. See
[actions.md](actions.md) for the full `Action` API.

- `.to_url(fn)` — a link, navigates to a page. **Checked first** — if set, the
  callback / modal never runs.
- `.modal(schema).action(fn)` — opens the schema's form in a modal bound to the
  row's record; `.action(fn)` persists it.
- `.modal(fn)` — renders `fn(record=...)` HTML in a modal.
- `.requires_confirmation()` / `.modal()` — a confirm dialog.
- `.action(fn)` alone — `hx-post`, then a toast + table refresh.
- `.collapsed()` — fold this action into a trailing **"⋯" menu**.
- `.icon(name)`, `.variant("secondary" | "danger" | …)`, `.visible(fn)`,
  `.authorize("app.perm" | fn)`.

Callback params are injected by name — `request`, `user`, `record` (row) /
`records` (bulk), `data` (a `.modal(schema)` form's cleaned data). See
[callbacks.md](callbacks.md).

## Row selection & bulk actions

`.bulk_actions([...])` adds a leading checkbox column and a toolbar that slides
in once rows are ticked. Selecting rows survives a client-mode filter round-trip.

Tick the header checkbox, then **"Select every matching row"**: the bulk action
receives the **filtered queryset itself** (unmaterialised), not a pk list — so
`records.update(...)` runs as one statement over millions of rows.

The endpoint re-scopes the ticked pks against `Table.get_action_queryset(request)`
(the same filters the user saw). A tampered pk from outside the current filter
cannot be reached.

```python
BulkAction.make("archive").requires_confirmation()
    .action(lambda records: records.update(status="archived"))
```

## Whole-row click & hover preview

| call | effect |
|---|---|
| `.record_url(fn)` | clicking a row (bar buttons/inputs) navigates to `fn(record)` (full page); ⌘/Ctrl-click opens a new tab; row is keyboard-focusable, Enter activates |
| `.record_action(action)` | a row click fires an `Action` — typically `.modal(...)` or `.to_url(...)` |
| `.record_preview(fn)` | hovering a row (~350 ms) pops a floating card with `fn(record)` HTML |

`record_url` wins if both `record_url` and `record_action` are set
(`tables/table.py:237-244`). Clicks on interactive descendants (buttons, links,
inputs, the selection checkbox, the "⋯" menu) never trigger the row action, and
text selection is ignored.

## Presentation — feed

`.presentation("feed")` renders rows as a borderless list. The first cell is the
title, middle cells the meta line, the last cell a trailing element (3+ columns).
Combine with `.client_side()` for a small always-in-page list.

```python
Table.make(Article.objects.order_by("-created_at")[:6])
    .columns([TextColumn.make("title"), TextColumn.make("author.name"), BadgeColumn.make("status")])
    .client_side().presentation("feed")
```

## Views & mixins

### `TableMixin` (`tables/views.py:15-43`)

- **MRO:** place `TableMixin` **before** the Django view (`TemplateView`,
  `ListView`) so `super().get()` / `super().get_context_data()` resolve to it.
  Place **auth mixins after** `TableMixin` — `dispatch` (where auth runs) still
  fires first, and the fragment is served from `get`, after `dispatch`.
- **Class attributes:** `table: Table | None = None`,
  `table_context_name = "table_html"`.
- **Override `get_table(self) -> Table`** to build the table per request.
  Returning `self.table` when `None` raises
  `ValueError(f"{type(self).__name__} needs a `table` or `get_table()`")`.
- `get()` — on an `HX-Request` whose `?_dcc_table` equals this table's id,
  returns `HttpResponse(table.render_content(request))` (the fragment); else
  `super().get(...)`. **Do not override** unless you reproduce that contract.
- `get_context_data()` adds `{table_context_name: table.render(request)}`.

In a panel `Resource`, the table comes from `build_table(*, request)` — see
[panels.md](panels.md).

## Calling a table directly

```python
table.render(request)            # full shell (SafeString)
table.render_content(request)    # just the content fragment
```

`render()` and `render_content()` both call `_register()` first, which registers
the table as an action owner if it has any actions.

## Callbacks

`record_url`, `record_action` targets, `record_preview`, and any column
`.state(fn)` / `.visible(fn)` are closures — injected by parameter name from
`{record, request, user, form, operation, context, component, get, state}`. See
[callbacks.md](callbacks.md).

## Constraints / do not combine

- `.infinite_scroll()` overrides `.page_numbers()` and `.stream()`.
- The rows-per-page picker needs `.paginate([>1 choices])` **and** server mode.
- `.client_side()` / `.server_side()` disable the row-count auto-probe — a table
  forced client-side with 100k rows renders 100k rows.
- `record_url` + `record_action` — `record_url` wins.
- A column `.state(fn)` returning HTML needs `.allow_html()` or it renders
  escaped.
- Reaching the action endpoint requires the table to have been rendered at least
  once in the process (so `_register()` ran) — a bare `Action` never rendered by
  an owner is a 404.

## Settings

| Key | Default | Effect |
|---|---|---|
| `TABLE_CLIENT_SIDE_MAX_ROWS` | `200` | client mode at or below this count |
| `TABLE_PER_PAGE_CHOICES` | `[10, 25, 50, 100]` | fallback page-size options; only the first is used unless `.paginate()` is called |

## Known sharp edges

- `ImageColumn.thumbnail(...)` swallows **any** exception from the thumbnail
  backend and falls back to the original image URL — a misconfigured backend
  fails silently in a table (it does raise elsewhere; see [images.md](images.md)).
- The grid width is fixed (100% of its container); height follows the row count
  on the page.
- `default_sort` is applied only when the querystring carries no sort; a user who
  has clicked a header keeps their choice.
- In streaming mode the sort falls back to `pk` if the current sort column is not
  `sortable` (`tables/table.py:413-418`).
