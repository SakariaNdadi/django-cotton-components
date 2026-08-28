from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from django_cotton_components.panels import Panel
from django_cotton_components.studio.deserialize import (
    build_schema_from_spec,
    build_table_from_spec,
)
from django_cotton_components.studio.models import DashboardSpec
from tests.testapp.models import Article, Author

pytestmark = pytest.mark.django_db

panel = Panel("studio").path("s").dynamic().auth(lambda r: r.user.is_authenticated)
urlpatterns = [panel.mount()]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__


@pytest.fixture
def spec():
    return DashboardSpec.objects.create(
        slug="articles",
        label="Articles",
        model="testapp.Article",
        table={
            "columns": [
                {"type": "TextColumn", "name": "title", "config": {"sortable": True}},
                {"type": "BadgeColumn", "name": "status"},
            ],
            "filters": [
                {
                    "type": "SelectFilter",
                    "name": "status",
                    "config": {"options": [["live", "Live"], ["draft", "Draft"]]},
                }
            ],
            "default_sort": "-title",
        },
        schema={
            "fields": ["title", "slug", "status", "author"],
            "layout": [
                {
                    "type": "Section",
                    "name": "Content",
                    "children": [
                        {"type": "TextInput", "name": "title", "config": {"required": True}},
                        {"type": "Select", "name": "status"},
                        {"type": "Select", "name": "author"},
                    ],
                }
            ],
        },
        infolist={"entries": [{"type": "TextEntry", "name": "title"}]},
    )


def test_table_spec_round_trips():
    table = build_table_from_spec(
        Article.objects.all(),
        {
            "columns": [
                {
                    "type": "TextColumn",
                    "name": "title",
                    "config": {"sortable": True, "searchable": True},
                },
            ]
        },
    )
    html = str(table.render(None))
    assert "Title" in html


def test_schema_spec_builds_a_working_form():
    schema = build_schema_from_spec(
        Article,
        {
            "fields": ["title", "slug"],
            "layout": [{"type": "TextInput", "name": "title", "config": {"required": True}}],
        },
    )
    form = schema.build_form(data={"title": "", "slug": "x"})
    assert not form.is_valid()  # title required -> real Django validation


def test_schema_spec_nested_layout_children():
    schema = build_schema_from_spec(
        Article,
        {
            "fields": ["title", "slug"],
            "layout": [
                {
                    "type": "Section",
                    "name": "Main",
                    "config": {"columns": 2},
                    "children": [
                        {"type": "TextInput", "name": "title"},
                        {"type": "TextInput", "name": "slug"},
                    ],
                },
            ],
        },
    )
    html = str(schema.render(form=schema.build_form()))
    assert "Main" in html and 'name="title"' in html and 'name="slug"' in html


def test_infolist_spec_and_default():
    from django_cotton_components.studio.deserialize import build_infolist_from_spec

    built = build_infolist_from_spec(Article, {"entries": [{"type": "TextEntry", "name": "title"}]})
    assert "dcc-infolist" in str(built.render(record=None))
    # no entries -> one per field
    default = build_infolist_from_spec(Article, {})
    assert "Title" in str(default.render(record=None))


def test_unknown_type_is_rejected():
    with pytest.raises(ValidationError):
        build_table_from_spec(Article.objects.all(), {"columns": [{"type": "Evil"}]})


def test_callable_setters_are_rejected():
    # `state` takes a closure at render time — not spec-expressible
    with pytest.raises(ValidationError):
        build_table_from_spec(
            Article.objects.all(),
            {"columns": [{"type": "TextColumn", "name": "x", "config": {"state": "os.system"}}]},
        )
    # a hostile setter name that isn't a @setter also fails
    with pytest.raises(ValidationError):
        build_table_from_spec(
            Article.objects.all(),
            {"columns": [{"type": "TextColumn", "name": "x", "config": {"__class__": 1}}]},
        )


def test_dashboardspec_validates_on_save():
    with pytest.raises(ValidationError):
        DashboardSpec.objects.create(slug="bad", model="nope.Missing", table={})
    with pytest.raises(ValidationError):
        DashboardSpec.objects.create(
            slug="bad2",
            model="testapp.Article",
            table={"columns": [{"type": "NotAColumn"}]},
        )


def test_dynamic_resource_serves_list_and_create(client, urlconf, spec, django_user_model):
    ada = Author.objects.create(name="Ada")
    Article.objects.create(title="Live one", slug="l1", status="live", author=ada)
    user = django_user_model.objects.create_superuser("root", "r@x.com", "x")
    client.force_login(user)

    r = client.get("/s/d/articles/")
    assert r.status_code == 200
    assert b"Live one" in r.content
    assert b"dcc-table" in r.content

    n0 = Article.objects.count()
    r = client.post(
        "/s/d/articles/new/",
        {"title": "From spec", "slug": "from-spec", "status": "draft", "author": ada.pk},
    )
    assert r.status_code == 302
    assert Article.objects.count() == n0 + 1


def test_dynamic_resource_in_navigation(rf, urlconf, spec, django_user_model):
    req = rf.get("/")
    req.user = django_user_model.objects.create_superuser("n", "n@x.com", "x")
    labels = [item["label"] for item in panel.navigation(req)]
    assert "Articles" in labels
