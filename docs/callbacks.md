# Callbacks & closures

Every place you hand the library a function, and its exact contract. Two
mechanisms are in play — know which one a given call site uses.

## Mechanism 1 — `evaluate()` (configuration closures)

Used by almost every `@setter` that accepts a value: `.label(fn)`, `.help_text(fn)`,
`.visible(fn)`, `.hidden(fn)`, `.when(fn)`, `.state(fn)`, `.authorize(fn)`,
`Table.record_url(fn)`, `Table.record_preview(fn)`, a widget's `.value(fn)` /
`.data(fn)`, and so on.

Rules (`core/evaluate.py:57-76`):

1. A non-callable passes through unchanged. **A class passes through un-instantiated**
   — `.state(MyThing)` returns the class, it does not call it.
2. A callable is invoked with **only the parameters it declares, by name**, from
   this set:

   | name | value |
   |---|---|
   | `record` | `ctx.record` — the row / object being rendered |
   | `request` | `ctx.request` |
   | `user` | `ctx.user` (`request.user` or `None`) |
   | `form` | `ctx.form` — the bound Django form (schemas) |
   | `operation` | `"create"` / `"edit"` / `"view"` |
   | `context` | the `RenderContext` itself |
   | `component` | the component instance being rendered |
   | `get` / `state` | `get("field_name")` → the current bound value of a sibling form field (or the `default` you pass) |
   | `set` | a no-op on the server render path — there is no live state to write back |

3. A callable declaring **any other name** (including a typo like `reqeust`)
   raises `ClosureInjectionError` at render time.

`*args` / `**kwargs`-only callables receive nothing.

```python
TextColumn.make("author.name").state(lambda record: record.author.get_full_name())
TextInput.make("published_at").visible(lambda get: get("status") == "live")  # once, at render
Action.make("delete").authorize(lambda user, record: record.owner_id == user.id)
```

## Mechanism 2 — `Action.action(fn)` (the action callback)

Used **only** by `.action(fn)` on an `Action` / `BulkAction`
(`actions/action.py:312-332`). Parameters are matched by name against a fixed
list; there is no `evaluate`, so `ClosureInjectionError` does not apply — an
undeclared parameter is a plain `TypeError` when the callback is called.

| param | single `Action` | `BulkAction` |
|---|---|---|
| `request` | the `HttpRequest` | same |
| `user` | `request.user` | same |
| `data` | cleaned data of a `.modal(schema)` form (`{}` otherwise) | same |
| `record` | the row (`records[0]` or `None`) | **not passed** |
| `records` | not passed | a list of rows, **or the unmaterialised `QuerySet`** for "select every matching row" |

Return value is ignored. The callback runs **uncaught** — raise to abort with a
500, or handle failure yourself. The success toast fires regardless of what the
callback did.

```python
def publish(records):  # BulkAction
    if isinstance(records, QuerySet):
        records.update(status="live")  # one statement, select-all
    else:
        for r in records:
            r.publish()
```

## Call-site reference

### Schema fields

| setter | mechanism | fires | contract |
|---|---|---|---|
| `.label / .help_text / .placeholder / .hint / .icon (fn)` | evaluate | on render | return the string (or `None`) |
| `.required / .disabled / .readonly (fn)` | evaluate | on render | return a bool; **cosmetic only** — real validation is on the form |
| `.visible / .hidden / .when / .hidden_when (fn)` | evaluate | on render | return a bool; evaluated **once** — not reactive. For reactive use `.visible_when(...)` (a compiled Alpine expression, no closure) |
| `.default(value)` | — | — | a plain value; used when no form is bound |

### Table

| setter | mechanism | fires | contract |
|---|---|---|---|
| `column.state(fn)` | evaluate (`ctx.child(record=...)`) | per cell | return the display value; wrap markup in `format_html` **and** add `.allow_html()` |
| `record_url(fn)` | evaluate | per row | return a URL string; falsy → no row link |
| `record_preview(fn)` | evaluate | per row (rendered eagerly) | return HTML (use `format_html`); shown on hover |
| `record_action(action)` | — | — | an `Action`; its own callback follows mechanism 2 |
| column `.visible(fn)` etc. | evaluate | on render | as schema fields |

### Actions

| setter | mechanism | contract |
|---|---|---|
| `.action(fn)` | mechanism 2 | see above |
| `.authorize("app.perm")` | — | `user.has_perm(perm, record)` — checked at render **and** POST |
| `.authorize(fn)` | evaluate | return a bool; checked at render **and** POST |
| `.visible(fn)` | evaluate | return a bool; hides the trigger |
| `.to_url(fn)` | evaluate | return a URL; **short-circuits** `.action` / `.modal` |
| `.modal(fn)` | evaluate (`record=`) | return HTML for the modal body |

### Infolist entries

| setter | mechanism | contract |
|---|---|---|
| `entry.state(fn)` | evaluate (`ctx.child(record=...)`) | return the value; output is **escaped** (no HTML opt-out) |

### Wizard

| hook | signature | fires | contract |
|---|---|---|---|
| `WizardStep.body` (callable form) | `body(view) -> str` | on render of that step | return markup |
| `WizardStep.record` | `record(view) -> record` | on render of an `Infolist` step | return a model / dict / `SimpleNamespace`; a dict is wrapped |
| `WizardView.done` | `done(self, form_list, **kwargs) -> HttpResponse` | after the last step re-validates | persist + return a response; **required override** |

### Panels

| hook | signature | fires | contract |
|---|---|---|---|
| `Panel.auth(*guards)` | `guard(request) -> bool` | before every panel page (`dispatch`) | falsy → `PermissionDenied` |
| `Resource.get_queryset` | `(request) -> QuerySet` | per request | the rows this resource exposes — the scoping boundary |
| `Resource.can` | `(request, action, obj=None) -> bool` | per page | `action` ∈ `{"view", "add", "change", "delete"}` |
| `Resource.build_table / build_schema / build_infolist` | `(cls, *, request) -> …` | per request | **classmethods** — never store request state on the class |

### Widgets

| setter / hook | mechanism | contract |
|---|---|---|
| `StatWidget.value(fn)` | `_resolve` (calls `fn(request)` if it wants `request`, else `fn()`) | return a scalar |
| `ChartWidget.data(fn)` / `BarListWidget.data(fn)` | same | return `[(label, value), …]` or a Chart.js `{labels, datasets}` dict |
| `TableWidget(label, table_fn)` | same | `table_fn(request) -> Table` |
| `Widget.context(self, request)` | override | return a dict for the content template |
| `Widget.payload(self, request)` | override | return a JSON-able dict for the Alpine component, or `None` |

## Constraints

- Do not raise from an `evaluate` closure to signal "hide" — return a falsy value.
  A raise there is a 500.
- A closure that needs the request user must declare `user` or `request`, spelled
  exactly.
- `get("field")` only works while a form is bound (schemas). Elsewhere it returns
  the default.
- `component` and `context` give you escape hatches, but a closure that reaches
  into `context.extra` is coupling to internals — prefer the named injectables.
