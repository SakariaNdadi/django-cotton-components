# Actions

## Mental model

An `Action` is a named, addressable operation on **one record**; a `BulkAction`
is the same on **many**. Tables and panel resources expose them.

The security model (`actions/registry.py:1-11`):

- The client only ever sends an **owner key** (`"table-articles"`) and an
  **action name** (`"publish"`) — both opaque strings registered at render time.
  Never an import path, a model label, or a callable. An unknown key is a **404**.
- The owner knows how to produce the queryset its actions may touch
  (`get_action_queryset(request)` — already filtered/scoped). On POST the
  endpoint **re-scopes** the target pks against that queryset, so a tampered pk
  cannot reach a row the user was never shown.
- Authorization is checked **twice** — when the trigger renders (a denied action
  renders `""`) **and** again on the POST (a hand-crafted POST gets `403`).

## Quick start

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

`Action.make(name, **kwargs)` — every setter below is also a constructor kwarg.

| setter | effect |
|---|---|
| `.label(str)` | button text (default: title-cased name) |
| `.icon(name)` | icon name, left of the label |
| `.variant(str)` / `.color(str)` | `secondary` (default), `primary`, `danger`, `ghost`, `link` |
| `.to_url(str \| fn)` | render as a plain `<a>` — navigate to a page instead of calling back |
| `.schema(schema)` | attach a schema whose form opens in a modal |
| `.modal(schema)` | `.schema(schema)` **and** flag `modal=True` |
| `.modal(fn)` | render `fn(record=...)` HTML in a modal |
| `.modal()` / `.requires_confirmation()` | a bare confirm dialog |
| `.modal_heading(str)` / `.modal_description(str)` | modal chrome |
| `.action(fn)` | the callback (see below) |
| `.success_notification(str)` | toast text on success (default: `"<Label> done."`) |
| `.visible(bool \| fn)` | hide the trigger per record |
| `.authorize("app.perm" \| fn)` | permission gate — checked at render **and** on POST |
| `.collapsed()` | (table row actions) fold into the trailing "⋯" menu |

`needs_modal` is `True` if any of `confirm` / `schema` / `modal` is set. It
switches the trigger from a direct POST-to-row into a GET-that-opens-a-modal. So
`.requires_confirmation()` alone forces the modal path.

## The callback — `.action(fn)`

Parameters are injected **by name** (`actions/action.py:312-332`):

| param | value |
|---|---|
| `record` | the row (single actions); `records[0]` or `None` |
| `records` | for a `BulkAction`: a list, **or the filtered `QuerySet`** for "select all matching" |
| `data` | cleaned data of a `.modal(schema)` form |
| `request` | the `HttpRequest` |
| `user` | `request.user` |

Declare only the names you need; any other parameter name is a `TypeError` from
the call (these are not run through `evaluate()`, so `ClosureInjectionError` does
not apply here — a plain `TypeError` does). For a `BulkAction`, `record` is
meaningless — use `records`.

```python
def save_quick_edit(record, data):
    record.title = data["title"]
    record.save(update_fields=["title"])

Action.make("quick_edit").modal(quick_edit_schema()).action(save_quick_edit)
```

Return value is ignored. Raise to abort — the exception propagates as a 500
(there is no catch around `action.run`).

## Request flow

One endpoint — `dcc:action`, from `django_cotton_components.urls`
(`a/<owner_key>/<action_name>/`). You mount it once; see [settings.md](settings.md).

- **GET** → render the confirm / schema modal into `#dcc-modal-<owner>`.
  - `403` if not authorized.
  - a `.schema(...)` action renders `schema.build_standalone_form(instance=...)`
    (only the declared fields — the parent form's other required fields do not
    block).
  - a `.modal(fn)` action renders `fn(record=...)`.
- **POST** → re-resolve, re-authorize (`403` on failure), re-scope the targets,
  validate the schema form (invalid → re-render the modal with errors, **HTTP
  200**), run the callback.

Response codes (`actions/endpoints.py:99-106`):

| case | status | headers |
|---|---|---|
| modal action succeeded | `200` with empty body | `HX-Trigger: {dcc:toast, dcc:refresh}` — htmx clears the mount, the dialog closes |
| inline (non-modal) action succeeded | `204` | `HX-Trigger: {dcc:toast, dcc:refresh}` — the row is not blanked; `dcc:refresh` repaints the table |
| schema form invalid | `200` | modal re-rendered with field errors |
| not authorized | `403` | |
| unknown owner/action | `404` | |

`dcc:refresh` is what makes a table (and any `auto_refresh` dashboard widget)
repaint after a mutation.

## Bulk actions

`BulkAction` has no record. The trigger sits in the table's bulk toolbar. The
ticked pks ride along as hidden inputs; the current filter/search state is baked
into the action URL. The endpoint re-scopes to exactly the rows the user saw.

With **"Select every matching row"** the callback receives the **unmaterialised
queryset** — `records.update(...)` runs as one statement:

```python
BulkAction.make("archive").requires_confirmation()
    .action(lambda records: records.update(status="archived"))
```

## Row-click actions

`Table.record_action(action)` fires an action when the whole row is clicked. It
supports `.to_url(...)` (navigate) and modal actions; a plain `.action(fn)` with
no modal does nothing on a row click. See
[tables.md](tables.md#whole-row-click--hover-preview).

## `render_trigger` / `render_modal`

`action.render_trigger(*, record=None, request=None)` returns the button HTML (or
`""` if not visible). Used by `Menu` to build a "⋯" menu of collapsed row
actions:

```python
Menu.make().items([
    edit_action.render_trigger(record=obj, request=request),
    delete_action.render_trigger(record=obj, request=request),
])
```

`action.render_modal(*, request, records, form_html="")` builds the Cancel /
Confirm modal; the endpoint calls it.

## Being an action owner

To expose actions from something other than a `Table`, implement the
`ActionOwner` protocol (`actions/registry.py:24-31`) and call
`registry.register(self)`:

| member | contract |
|---|---|
| `key` (property) | the opaque owner key the client will send |
| `get_action_queryset(request)` | the rows these actions may touch — **already** scoped to the user's visibility and the current filters. This is the security boundary. |
| `get_actions()` | `{name: Action}`; call `action.bind_owner(self.key)` on each |

## Constraints / do not combine

- **`.to_url()` short-circuits everything.** If `link` is set, the action renders
  as a plain `<a>` and `.action(fn)` / `.modal(...)` are never invoked
  (`actions/action.py:219-222`). Do not set both.
- `.schema(schema)` and `.modal(schema)` write the same slot; `.modal(schema)`
  additionally flags `modal=True`. Prefer `.modal(schema)` when you want the
  modal.
- `action.url()` before `bind_owner()` → `AssertionError("Action not bound to an
  owner")`. An action must be returned by a registered owner's `get_actions()` to
  be reachable — a constructed-but-unexposed action is a 404.
- `BulkAction` + a callback declaring `record` → `record` is never passed. Use
  `records`.
- The callback runs uncaught — validate inside it and let exceptions be 500s, or
  handle them yourself.

## Settings

Actions read no `DCC[...]` keys directly. The endpoint URL prefix is your mount
point (`URL_PREFIX` default `"dcc/"`); see [settings.md](settings.md).

## Known sharp edges

- `.variant()` on an action is passed straight to `ui.Button.variant()`, which
  **warns and falls back to `secondary`** for an unknown value.
- A `.modal(schema)` action always builds a *standalone* form of the declared
  fields — model fields you did not declare are not saved by the callback's
  `data`; fetch them off `record` or widen the schema.
- The success toast fires even if your callback silently did nothing; word
  `.success_notification(...)` accordingly or raise on failure.
