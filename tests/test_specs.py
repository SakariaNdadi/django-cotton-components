from __future__ import annotations

import json

import pytest
from django.core.exceptions import ValidationError

from django_cotton_components.panels import Panel
from django_cotton_components.studio.deserialize import (
    build_schema_from_spec,
    build_table_from_spec,
    build_widgets_from_spec,
)
from django_cotton_components.studio.models import DashboardSpec, PanelDashboard
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


def _chart_payload(widget):
    html = str(widget.render(None))
    blob = html.split('type="application/json">', 1)[1].split("</script>", 1)[0]
    return json.loads(blob)


def test_widgets_spec_round_trips():
    widgets = build_widgets_from_spec(
        [
            {"type": "StatWidget", "name": "Total", "config": {"value": 5}},
            {
                "type": "ChartWidget",
                "name": "Split",
                "config": {"kind": "bar", "data": [["a", 1], ["b", 2]]},
            },
        ]
    )
    assert len(widgets) == 2
    assert "5" in str(widgets[0].render(None))
    assert _chart_payload(widgets[1])["data"]["datasets"][0]["data"] == [1, 2]


def test_widgets_spec_unknown_type_rejected():
    with pytest.raises(ValidationError):
        build_widgets_from_spec([{"type": "EvilWidget"}])


def test_widgets_spec_callable_setter_rejected():
    with pytest.raises(ValidationError):
        build_widgets_from_spec(
            [{"type": "StatWidget", "name": "x", "config": {"visible": "os.system"}}]
        )


def test_paneldashboard_rejects_non_allowlisted_query(settings):
    settings.DCC = {"STUDIO_MODELS": []}
    with pytest.raises(ValidationError):
        PanelDashboard.objects.create(
            slug="m",
            widgets=[
                {
                    "type": "ChartWidget",
                    "name": "c",
                    "config": {"query": {"model": "testapp.Article", "group_by": "status"}},
                }
            ],
        )


def test_paneldashboard_query_chart_renders_aggregation(settings, author):
    settings.DCC = {"STUDIO_MODELS": ["testapp.Article"]}
    Article.objects.create(title="a", slug="a", status="live", author=author)
    Article.objects.create(title="b", slug="b", status="live", author=author)
    Article.objects.create(title="c", slug="c", status="draft", author=author)
    dashboard = PanelDashboard.objects.create(
        slug="metrics",
        label="Metrics",
        widgets=[
            {
                "type": "ChartWidget",
                "name": "By status",
                "config": {
                    "kind": "bar",
                    "query": {
                        "model": "testapp.Article",
                        "group_by": "status",
                        "aggregate": "count",
                    },
                },
            }
        ],
    )
    widget = build_widgets_from_spec(dashboard.widgets)[0]
    payload = _chart_payload(widget)
    assert payload["data"]["labels"] == ["draft", "live"]
    assert payload["data"]["datasets"][0]["data"] == [1, 2]


def test_dynamic_dashboard_route_serves_widgets(
    client, urlconf, settings, author, django_user_model
):
    settings.DCC = {"STUDIO_MODELS": ["testapp.Article"]}
    Article.objects.create(title="a", slug="a", status="live", author=author)
    PanelDashboard.objects.create(
        slug="metrics",
        label="Metrics",
        widgets=[
            {
                "type": "StatWidget",
                "name": "Total",
                "config": {"query": {"model": "testapp.Article", "aggregate": "count"}},
            }
        ],
    )
    user = django_user_model.objects.create_superuser("root", "r@x.com", "x")
    client.force_login(user)
    resp = client.get("/s/dash/metrics/")
    assert resp.status_code == 200
    assert b"Metrics" in resp.content
    assert b"dcc-widget--stat" in resp.content


def test_paneldashboard_in_navigation(rf, urlconf, django_user_model):
    PanelDashboard.objects.create(slug="metrics", label="Metrics", widgets=[])
    req = rf.get("/")
    req.user = django_user_model.objects.create_superuser("n2", "n2@x.com", "x")
    assert "Metrics" in [item["label"] for item in panel.navigation(req)]


def test_dynamic_resource_in_navigation(rf, urlconf, spec, django_user_model):
    req = rf.get("/")
    req.user = django_user_model.objects.create_superuser("n", "n@x.com", "x")
    labels = [item["label"] for item in panel.navigation(req)]
    assert "Articles" in labels
