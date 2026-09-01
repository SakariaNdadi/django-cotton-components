"""The sidebar builder: gating, GET render, save round-trip, preview."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Permission
from django.urls import include, path

from django_control_components.panels import Panel
from django_control_components.panels.resource import Resource
from django_control_components.studio.models import NavItem
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


class ArticleResource(Resource):
    model = Article


panel = (
    Panel("s")
    .path("s")
    .resources([ArticleResource])
    .studio()
    .auth(lambda r: r.user.is_authenticated)
)
urlpatterns = [
    panel.mount(),
    path("studio/", include("django_control_components.studio.urls")),
]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__
    settings.LOGIN_URL = "/accounts/login/"


@pytest.fixture
def studio_user(django_user_model):
    user = django_user_model.objects.create_user("editor", password="x")
    user.user_permissions.add(Permission.objects.get(codename="use_studio"))
    return django_user_model.objects.get(pk=user.pk)


def test_anonymous_redirected_to_login(client, urlconf):
    assert client.get("/studio/nav/s/").status_code == 302


def test_authenticated_without_permission_gets_403(client, urlconf, django_user_model):
    client.force_login(django_user_model.objects.create_user("plain", password="x"))
    assert client.get("/studio/nav/s/").status_code == 403


def test_builder_renders_for_studio_user(client, urlconf, studio_user):
    client.force_login(studio_user)
    response = client.get("/studio/nav/s/")
    assert response.status_code == 200
    assert b"dccStudioDoc" in response.content
    assert b"nav-boot" in response.content


def test_studio_home_is_a_hub(client, urlconf, studio_user):
    client.force_login(studio_user)
    response = client.get("/studio/")
    assert response.status_code == 200
    assert b"/studio/nav/s/" in response.content
    assert b"/studio/dashboards/" in response.content
    assert b"/studio/resources/" in response.content


def test_save_round_trips_with_group_nesting(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {
        "items": [
            {"id": "a", "label": "Content", "target_kind": "group"},
            {"id": "b", "label": "Articles", "target_kind": "resource", "target": "article"},
            {"id": "c", "label": "Docs", "target_kind": "url", "target": "/docs/"},
        ]
    }
    response = client.post("/studio/nav/s/save/", {"doc": json.dumps(doc), "revision": 0})
    assert response.status_code == 200
    assert response.json()["revision"] == 1

    rows = list(NavItem.objects.filter(panel="s").order_by("order"))
    assert [r.label for r in rows] == ["Content", "Articles", "Docs"]
    group, articles, docs = rows
    assert articles.parent_id == group.pk
    assert docs.parent_id == group.pk


def test_save_is_non_destructive_and_keeps_access_grants(client, urlconf, studio_user):
    """An in-place update must not wipe RolesView-managed access fields."""
    from django.contrib.auth.models import Group

    client.force_login(studio_user)
    first = {"items": [{"id": "a", "label": "Docs", "target_kind": "url", "target": "/docs/"}]}
    r1 = client.post("/studio/nav/s/save/", {"doc": json.dumps(first), "revision": 0})
    assert r1.json()["revision"] == 1

    row = NavItem.objects.get(panel="s")
    group = Group.objects.create(name="editors")
    row.groups.add(group)
    row.required_permission = "testapp.view_article"
    row.save()

    second = {
        "items": [
            {
                "id": f"db{row.pk}",
                "label": "Documentation",
                "target_kind": "url",
                "target": "/docs/",
            }
        ]
    }
    r2 = client.post("/studio/nav/s/save/", {"doc": json.dumps(second), "revision": 1})
    assert r2.json()["revision"] == 2

    row.refresh_from_db()
    assert row.label == "Documentation"
    assert row.pk == NavItem.objects.get(panel="s").pk  # same row, not recreated
    assert list(row.groups.values_list("name", flat=True)) == ["editors"]
    assert row.required_permission == "testapp.view_article"


def test_save_rejects_stale_revision(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "Docs", "target_kind": "url", "target": "/docs/"}]}
    client.post("/studio/nav/s/save/", {"doc": json.dumps(doc), "revision": 0})
    stale = client.post("/studio/nav/s/save/", {"doc": json.dumps(doc), "revision": 0})
    assert stale.status_code == 409
    assert stale.json()["revision"] == 1
    assert stale.json()["doc"]["items"][0]["label"] == "Docs"


def test_save_rejects_unknown_kind(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "X", "target_kind": "wormhole"}]}
    response = client.post("/studio/nav/s/save/", {"doc": json.dumps(doc), "revision": 0})
    assert response.status_code == 422
    assert "wormhole" in response.json()["errors"][0]["message"]


def test_save_rejects_missing_label(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "  ", "target_kind": "url", "target": "/x/"}]}
    response = client.post("/studio/nav/s/save/", {"doc": json.dumps(doc), "revision": 0})
    assert response.status_code == 422


def test_preview_renders_a_nav_fragment(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "Docs", "target_kind": "url", "target": "/docs/"}]}
    response = client.post("/studio/nav/s/preview/", {"doc": json.dumps(doc)})
    assert response.status_code == 200
    assert b"Docs" in response.content


def test_save_then_reload_prefills_the_builder(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "Docs", "target_kind": "url", "target": "/docs/"}]}
    client.post("/studio/nav/s/save/", {"doc": json.dumps(doc), "revision": 0})
    response = client.get("/studio/nav/s/")
    assert b"Docs" in response.content


def test_palette_api_gated_and_returns_types(client, urlconf, studio_user):
    client.force_login(studio_user)
    response = client.get("/studio/api/palette/")
    assert response.status_code == 200
    assert "columns" in response.json()


def test_models_api(client, urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root-m", "m@x.io", "x")
    client.force_login(root)
    response = client.get("/studio/api/models/")
    assert response.status_code == 200
    labels = {row["label"] for row in response.json()["models"]}
    assert "testapp.article" in labels
    assert "auth.group" not in labels


def test_model_fields_api(client, urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root-f", "f@x.io", "x")
    client.force_login(root)
    response = client.get("/studio/api/models/testapp.article/")
    assert response.status_code == 200
    names = {f["name"] for f in response.json()["fields"]}
    assert "title" in names
    assert client.get("/studio/api/models/auth.group/").status_code == 404
    assert client.get("/studio/api/models/no.such/").status_code == 404
