# Wizards

Multi-step forms on top of `django-formtools`. `formtools` already solves step
storage, inter-step file handling, step re-entry and `done()`; the wizard here
swaps only the **rendering layer** for a DCC [`Schema`](schemas.md) per step.
Per-step validation is Django's `form.is_valid()` — there is no parallel system.

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

`form_list` for each step is derived from the step's schema —
`schema.to_form_class()` builds a real Django form containing **only that step's
declared fields**.

## Template

```django
{% load dcc_tags %}
<div id="{{ wizard_id }}">
  {{ wizard_htmx }}                      {# hx-post + hx-select on the wrapper #}
  <ol class="wizard-steps">
    {% for name, title in step_titles %}
      <li class="{% if name == current_step %}is-current{% endif %}">{{ title }}</li>
    {% endfor %}
  </ol>
  <form {{ wizard_htmx }} method="post">
    {% csrf_token %}
    {{ schema_html }}
    <button type="submit">Next</button>
  </form>
</div>
```

Each step submits over htmx and swaps only `#<wizard_id>` back in — the view
still renders the full page, so **with JavaScript disabled the plain full-page
POST flow is unchanged**.

Context provided by the view: `schema_html`, `step_titles` (`[(name, title)]`),
`current_step`, `wizard_id`, `wizard_htmx`.

## Guarantees

`render_done()` re-validates every prior step before calling `done()`, so a
hand-crafted POST cannot skip ahead. `done()` must be implemented — the base
raises `NotImplementedError`.
