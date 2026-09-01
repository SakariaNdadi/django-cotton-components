# Panels & Resources

A **Panel** is a mount point for a set of **Resources**. A Resource wires one
Django model to four pages — list, create, edit, view — built from the same
`Schema` and `Table` builders you use elsewhere. It is Filament-inspired CRUD
scaffolding on plain class-based views: no Livewire, no server-held component
state, and it touches none of `django.contrib.admin`'s machinery, so the two run
side by side.

Use a panel when you want a branded, permission-gated admin area that you shape
in Python — not a replacement for `django-admin`, and not a place for one-off
pages (yet — see *Custom pages* below).

## Define a resource

```python
# app/panels.py
from django_control_components.panels import Panel, Resource
from django_control_components.schemas import Schema, Section, TextInput, Select
from django_control_components.tables import Table, TextColumn, DateColumn, SelectFilter

from .models import Article


class ArticleResource(Resource):
    model = Article
    navigation_icon = "newspaper"  # any active-icon-set name
    navigation_group = "Content"  # optional sidebar grouping

    @classmethod
    def build_table(cls, *, request):
        return (
            Table.make(cls.get_queryset(request).select_related("author"))
            .id("panel-articles")
            .columns(
                [
                    TextColumn.make("title").sortable().searchable().limit(60),
                    TextColumn.make("author.name")
                    .label("Author")
                    .sortable(sort_field="author__name"),
                    DateColumn.make("created_at").since().sortable(),
                ]
            )
            .filters([SelectFilter.make("status").options(Article.Status.choices)])
            .default_sort("-created_at")
        )

    @classmethod
    def build_schema(cls, *, request):
        return (
            Schema.make()
            .model(Article, fields=["title", "slug", "status", "body"])
            .schema(
                [
                    Section.make("Content").schema(
                        [
                            TextInput.make("title").required(),
                            TextInput.make("slug").required(),
                            Select.make("status"),
                        ]
                    ),
                ]
            )
        )
```

Everything is a **classmethod that takes `request`** — never a class attribute —
so per-request state (tenant scoping, the current user) cannot leak between
requests. Override only what you need; the defaults build a five-column table
and a full ModelForm schema.

Override points:

| method | default | use it for |
|---|---|---|
| `build_table(*, request)` | first 5 scalar fields | the list page's `Table` |
| `build_schema(*, request)` | `Schema.make().form(modelform_factory(model))` | the create/edit form |
| `build_infolist(*, request)` | every field as a text entry | the view page (see [infolists.md](infolists.md)) |
| `get_queryset(request)` | `model._default_manager.all()` | row-level / tenant scoping |
| `can(request, action, obj=None)` | Django model perms, superuser bypass | object-level authorization |

`action` is one of `"view"`, `"add"`, `"change"`, `"delete"`.

## Mount the panel

```python
# config/urls.py
from django.urls import path
from app.panels import ArticleResource
from django_control_components.panels import Panel

admin_panel = (
    Panel("admin")
    .path("panel")  # -> /panel/...
    .resources([ArticleResource])
    .auth(lambda request: request.user.is_staff)  # panel-wide guard(s)
)

urlpatterns = [
    admin_panel.mount(),  # /panel/article/, /panel/article/new/, ...
    # ...
]
```

`.auth(*guards)` runs before every page; each guard is `HttpRequest -> bool` and
a falsy result raises `PermissionDenied`. Add more with repeated `.auth()` calls.
Per-resource `can()` runs after the panel guard.

Routes per resource: `{slug}/`, `{slug}/new/`, `{slug}/<pk>/`, `{slug}/<pk>/edit/`,
`{slug}/<pk>/delete/`. URL names are `{namespace}:{slug}-{list|create|view|edit|delete}`
where the namespace is `dcc-panel-{panel-name}`.

## Skin a panel

The package ships a minimal shell at
`django_control_components/panels/base.html`. Shadow it from your app to drop
panel pages into your own chrome:

```django
{# app/templates/django_control_components/panels/base.html #}
{% extends "app/base.html" %}
{% block crumbs %} / {{ resource_label }}{% endblock %}
```

The list/create/edit/view templates fill `{% block content %}`; context gives you
`panel`, `resource_label`, `nav` (a list of `{label, url, icon, group}`), and —
per page — `table_html`, `schema_html`, or `infolist_html`.

A dashboard page is a grid of widgets — see [widgets.md](widgets.md) for
`StatWidget`, `ChartWidget` (Chart.js), `BarListWidget`, `TableWidget`, custom
widgets, and stored `PanelDashboard` rows.

## Not built yet

- **Relation managers** — inline CRUD of related records on an edit page.
- **Global search** across resources.

See [no-code.md](no-code.md) for building resources from stored configuration
instead of Python subclasses.
