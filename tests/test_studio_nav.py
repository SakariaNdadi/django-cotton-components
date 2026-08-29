"""The sidebar builder: gating, GET render, save round-trip, preview."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Permission

from django_cotton_components.panels import Panel
from django_cotton_components.panels.resource import Resource
from django_cotton_components.studio.models import NavItem
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
urlpatterns = [panel.mount()]


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
    assert client.get("/s/studio/nav/").status_code == 302


def test_authenticated_without_permission_gets_403(client, urlconf, django_user_model):
    client.force_login(django_user_model.objects.create_user("plain", password="x"))
    assert client.get("/s/studio/nav/").status_code == 403


def test_builder_renders_for_studio_user(client, urlconf, studio_user):
    client.force_login(studio_user)
    response = client.get("/s/studio/nav/")
    assert response.status_code == 200
    assert b"dccStudioDoc" in response.content
    assert b"nav-boot" in response.content


def test_studio_home_is_a_hub(client, urlconf, studio_user):
    client.force_login(studio_user)
    response = client.get("/s/studio/")
    assert response.status_code == 200
    assert b"/s/studio/nav/" in response.content
    assert b"/s/studio/dashboards/" in response.content
    assert b"/s/studio/resources/" in response.content


def test_save_round_trips_with_group_nesting(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {
        "items": [
            {"id": "a", "label": "Content", "target_kind": "group"},
            {"id": "b", "label": "Articles", "target_kind": "resource", "target": "article"},
            {"id": "c", "label": "Docs", "target_kind": "url", "target": "/docs/"},
        ]
    }
    response = client.post("/s/studio/nav/save/", {"doc": json.dumps(doc)})
    assert response.status_code == 200
    assert response.json()["revision"] == 1

    rows = list(NavItem.objects.filter(panel="s").order_by("order"))
    assert [r.label for r in rows] == ["Content", "Articles", "Docs"]
    group, articles, docs = rows
    assert articles.parent_id == group.pk
    assert docs.parent_id == group.pk


def test_save_rejects_unknown_kind(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "X", "target_kind": "wormhole"}]}
    response = client.post("/s/studio/nav/save/", {"doc": json.dumps(doc)})
    assert response.status_code == 422
    assert "wormhole" in response.json()["errors"][0]["message"]


def test_save_rejects_missing_label(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "  ", "target_kind": "url", "target": "/x/"}]}
    response = client.post("/s/studio/nav/save/", {"doc": json.dumps(doc)})
    assert response.status_code == 422


def test_preview_renders_a_nav_fragment(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "Docs", "target_kind": "url", "target": "/docs/"}]}
    response = client.post("/s/studio/nav/preview/", {"doc": json.dumps(doc)})
    assert response.status_code == 200
    assert b"Docs" in response.content


def test_save_then_reload_prefills_the_builder(client, urlconf, studio_user):
    client.force_login(studio_user)
    doc = {"items": [{"id": "a", "label": "Docs", "target_kind": "url", "target": "/docs/"}]}
    client.post("/s/studio/nav/save/", {"doc": json.dumps(doc)})
    response = client.get("/s/studio/nav/")
    assert b"Docs" in response.content


def test_palette_api_gated_and_returns_types(client, urlconf, studio_user):
    client.force_login(studio_user)
    response = client.get("/s/studio/api/palette/")
    assert response.status_code == 200
    assert "columns" in response.json()


def test_models_api(client, urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root-m", "m@x.io", "x")
    client.force_login(root)
    response = client.get("/s/studio/api/models/")
    assert response.status_code == 200
    labels = {row["label"] for row in response.json()["models"]}
    assert "testapp.article" in labels
    assert "auth.group" not in labels


def test_model_fields_api(client, urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root-f", "f@x.io", "x")
    client.force_login(root)
    response = client.get("/s/studio/api/models/testapp.article/")
    assert response.status_code == 200
    names = {f["name"] for f in response.json()["fields"]}
    assert "title" in names
    assert client.get("/s/studio/api/models/auth.group/").status_code == 404
    assert client.get("/s/studio/api/models/no.such/").status_code == 404
