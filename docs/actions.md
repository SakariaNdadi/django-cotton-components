# Actions

An `Action` is a named, addressable operation on one record (or, as a
`BulkAction`, on many). Tables, resources and (later) other owners expose them;
the client only ever sends an **owner key** and an **action name**, both opaque
strings registered at render time. An unknown key is a 404, never a stack trace.

```python
from django_cotton_components.actions import Action, BulkAction

Action.make("publish")
    .label("Publish")
    .icon("rocket")
    .variant("secondary")
    .requires_confirmation()
    .modal_heading("Publish this article?")
    .action(lambda record: record.publish())
    .success_notification("Published")
```

## Setters

| setter | effect |
|---|---|
| `.label(str)` | button text (defaults to a title-cased name) |
| `.icon(name)` | FontAwesome icon name |
| `.variant(str)` / `.color(str)` | `secondary` (default), `primary`, `danger`, `ghost`, `link` |
| `.to_url(str \| fn)` | render as a plain `<a>` — navigate to a page instead of calling back |
| `.modal(schema)` | open that `Schema`'s form in a modal, bound to the record; pair with `.action(fn)` to persist |
| `.modal(fn)` | render `fn(record=...)` HTML in a modal |
| `.modal()` / `.requires_confirmation()` | a bare confirm dialog |
| `.modal_heading(str)` / `.modal_description(str)` | modal chrome |
| `.action(fn)` | the callback (see below) |
| `.success_notification(str)` | toast text on success |
| `.visible(bool \| fn)` | hide the trigger per-record |
| `.authorize("app.perm" \| fn)` | permission gate — checked at render **and** on POST |
| `.collapsed()` | (table row actions) fold into the trailing "⋯" menu |

## The callback

`.action(fn)` arguments are injected by parameter name:

| param | value |
|---|---|
| `record` | the row (single actions) |
| `records` | list, or the filtered **queryset** for "select all matching" (bulk) |
| `data` | cleaned data of a `.modal(schema)` form |
| `request` | the `HttpRequest` |
| `user` | `request.user` |

```python
def save_quick_edit(record, data):
    record.title = data["title"]
    record.save(update_fields=["title"])

Action.make("quick_edit").modal(quick_edit_schema()).action(save_quick_edit)
```

## Request flow

One endpoint — `dcc:action`, from `django_cotton_components.urls` (you mount it,
see the README Install section):

- **GET** → render the confirm / schema modal into `#dcc-modal-<owner>`.
- **POST** → re-authorize, re-scope the target(s) to the owner's queryset
  (a tampered pk can't reach a hidden row), validate the schema form, run the
  callback.

On success a modal action returns an **empty 200** (htmx clears the mount → the
dialog closes) plus `HX-Trigger: {dcc:toast, dcc:refresh}`. Inline non-modal
actions return `204` and let the `dcc:refresh` repaint the table. A schema form
that fails validation re-renders the modal with errors.

## Bulk actions

`BulkAction` has no record. The trigger sits in the table's bulk toolbar; the
ticked pks ride along as hidden inputs and the current filter/search state is
baked into the action URL, so the endpoint re-scopes to exactly the rows the
user saw. With **"Select every matching row"** the callback gets the unmaterialised
queryset — `records.update(...)` runs as one statement.

## Row-click actions

`Table.record_action(action)` fires an action when the whole row is clicked —
use `.modal(...)` for a slide-over detail view or `.to_url(...)` to navigate.
See [tables.md](tables.md#whole-row-click--hover-preview).
