# Migrating from 0.1.x to 1.0

1.0 is a hard break. The old templates were defective (unescaped JS
interpolation, a table that shipped every row's full model dict to the browser)
and are not carried forward. There is no compatibility shim.

## Template tag names

| 0.1.x | 1.0 |
|---|---|
| `<c-dcc-input>` | `<c-dcc.form.input>` |
| `<c-dcc-textarea>` | `<c-dcc.form.textarea>` |
| `<c-dcc-input.password>` | `<c-dcc.form.password>` |
| `<c-dcc-select>` | `<c-dcc.form.select>` |
| `<c-dcc-select-multiple>` | `<c-dcc.form.multi-select>` |
| `<c-dcc-checkbox>` | `<c-dcc.form.checkbox>` |
| `<c-dcc-radio>` | `<c-dcc.form.radio>` |
| `<c-dcc-toggle>` | `<c-dcc.form.toggle>` |
| `<c-dcc-button>` | `<c-dcc.button>` |
| `<c-dcc-h>` | `<c-dcc.heading>` |
| `<c-dcc-modal>` | `<c-dcc.modal>` |
| `<c-dcc-table>` | *removed — use `Table.make(...)` (Python)* |

## Styling

Components now emit semantic classes (`dcc-input`, `dcc-btn dcc-btn--primary`).
The `class` prop **merges** with those instead of replacing them. Load the
prebuilt stylesheet with `{% dcc_assets %}` in your base template, or point your
Tailwind 4 build at the source:

```css
@source "../../.venv/lib/python*/site-packages/django_cotton_components";
```

## Preferred path: build UI in Python

```python
from django_cotton_components.schemas import Schema, Section, TextInput, Select

schema = (
    Schema.make()
    .form(ArticleForm)
    .components(
        [
            Section.make("Content")
            .columns(2)
            .schema(
                [
                    TextInput.make("title").required(),
                    Select.make("status"),
                ]
            ),
        ]
    )
)
```

Render with the `SchemaFormMixin` on a `FormView`, or `{% dcc_form schema %}` in
a template.

## Errors

Field errors render server-side from `form.errors`. Remove any `errorTimer`,
`errorDivClass`, or `validationUrl` props — use `.live()` on a field for opt-in
debounced validation instead.
