# Wizards

Multi-step forms on top of `django-formtools`. `formtools` already solves step
storage, inter-step file handling, step re-entry and `done()`; the wizard here
swaps only the **rendering layer**. Per-step validation is Django's
`form.is_valid()` — there is no parallel system.

```bash
pip install "django-cotton-components[wizard]"
```

```python
from django_cotton_components.wizards import WizardView, WizardStep
from django_cotton_components.schemas import Schema, TextInput

class ArticleWizard(WizardView):
    template_name = "articles/wizard.html"
    steps_config = [
        WizardStep(
            "content",
            Schema.make().form(ArticleForm).strict().schema([
                TextInput.make("title"), TextInput.make("slug"),
            ]),
            title="Content",
        ),
        WizardStep(
            "publish",
            Schema.make().form(ArticleForm).strict().schema([TextInput.make("status")]),
            title="Publish",
        ),
    ]

    def done(self, form_list, **kwargs):
        data = {}
        for form in form_list:
            data.update(form.cleaned_data)
        Article.objects.create(**data)
        return redirect("article-list")
```

`form_list` for a form step is derived from the step's schema —
`schema.to_form_class()` builds a real Django form containing **only that step's
declared fields**.

## Step bodies

`WizardStep(name, body, ...)` — `body` is polymorphic:

| `body` | Step is | Use |
|---|---|---|
| `Schema` | a form step | collect and validate fields (default) |
| `Infolist` | a read-only detail step | review collected data, show a record |
| `str` / `SafeString` | raw markup | intro screen, static instructions |
| `callable(view) -> str` | rendered markup | "what changed" notes that need live data |

Non-form bodies get an empty always-valid form, so **`Next` never blocks** on
them and they contribute nothing to `form_list` / `get_all_cleaned_data()`.

```python
from django_cotton_components.infolists import Infolist, TextEntry

steps_config = [
    WizardStep(
        "intro",
        "<p>This wizard publishes an article in three steps. "
        "Nothing is saved until the final step.</p>",
        title="Start",
        heading="Before you begin",
    ),
    WizardStep("content", article_content_schema(), title="Content"),
    WizardStep("publish", article_publish_schema(), title="Publish"),
    WizardStep(
        "review",
        Infolist.make().schema([
            TextEntry.make("title"), TextEntry.make("slug"), TextEntry.make("status"),
        ]),
        title="Review",
        heading="Confirm and publish",
        record=lambda view: view.get_all_cleaned_data(),
    ),
]
```

`record` is called with the view and its return is the record the `Infolist`
renders against; a `dict` (e.g. `get_all_cleaned_data()`) is wrapped in a
`SimpleNamespace` automatically.

`heading` and `description` are optional per-step strings rendered above the body.

## Theming

Chrome is themed per subclass — no template override needed:

```python
class ArticleWizard(WizardView):
    wizard_class = "article-wizard"          # extra class on .dcc-wizard
    wizard_attrs = {                         # attributes on the wrapper
        "style": "--dcc-wizard-bg:#0b1120;"
                 "--dcc-wizard-pad:2rem;"
                 "--dcc-wizard-accent:#6366f1;"
                 "--dcc-wizard-accent-fg:#fff",
    }
    show_step_nav = True                     # set False to drop the step <ol>
```

Wizard-scoped CSS custom properties (defaults shown):

| Property | Default | Effect |
|---|---|---|
| `--dcc-wizard-bg` | `transparent` | wrapper background |
| `--dcc-wizard-accent` | `var(--dcc-primary)` | current-step chip background |
| `--dcc-wizard-accent-fg` | `var(--dcc-primary-fg)` | current-step chip text |
| `--dcc-wizard-pad` | `0` | wrapper padding |
| `--dcc-wizard-radius` | `var(--dcc-radius)` | wrapper corner radius |

For full structural control set `template_name` to your own template.

## Template

```django
{% load dcc_tags %}
<div class="dcc-wizard {{ wizard_class }}" id="{{ wizard_id }}"{{ wizard_attrs_html }}>
  {% if show_step_nav %}
  <ol class="dcc-wizard__steps">
    {% for step in steps %}
      <li class="dcc-wizard__step{% if step.is_current %} is-current{% endif %}{% if step.is_done %} is-done{% endif %}">
        {% if step.can_goto %}
          <button type="submit" form="{{ wizard_id }}-form" name="wizard_goto_step"
            value="{{ step.name }}" formnovalidate class="dcc-wizard__step-link">{{ step.title }}</button>
        {% else %}{{ step.title }}{% endif %}
      </li>
    {% endfor %}
  </ol>
  {% endif %}
  {% if step_heading %}<h2>{{ step_heading }}</h2>{% endif %}
  {% if step_description %}<p>{{ step_description }}</p>{% endif %}
  <form id="{{ wizard_id }}-form" {{ wizard_htmx }} method="post" enctype="multipart/form-data">
    {% csrf_token %}
    {{ wizard.management_form }}
    {{ step_html }}
    <button type="submit">Next</button>
  </form>
</div>
```

The step `<ol>` sits outside the `<form>` (its goto buttons target it by
`form="{{ wizard_id }}-form"`) so pressing Enter in a field always submits
`Next`, never a jump back.

Each step submits over htmx and swaps only `#<wizard_id>` back in — the view
still renders the full page, so **with JavaScript disabled the plain full-page
POST flow is unchanged**.

Context provided by the view:

| Var | Meaning |
|---|---|
| `step_html` | rendered body of the current step (`schema_html` is a back-compat alias) |
| `step_heading`, `step_description` | per-step strings, `""` when unset |
| `steps` | `[{name, title, is_current, is_done, can_goto}]` |
| `step_titles` | `[(name, title)]` — back-compat alias |
| `current_step` | current step name |
| `all_data` | `get_all_cleaned_data()`, or `{}` if a prior step is invalid |
| `wizard_id`, `wizard_htmx` | wrapper id and htmx attributes |
| `wizard_class`, `wizard_attrs_html`, `show_step_nav` | theming hooks |

Prior steps in `steps` carry `can_goto=True`; the `wizard_goto_step` button jumps
back to them. Forward navigation stays validation-gated by `formtools`.

## Guarantees

`render_done()` re-validates every prior step before calling `done()`, so a
hand-crafted POST cannot skip ahead. `done()` must be implemented — the base
raises `NotImplementedError`.
