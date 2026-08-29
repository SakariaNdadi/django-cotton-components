"""The resource builder: scaffold-from-model, columns/filters save, preview."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Permission

from django_cotton_components.panels import Panel
from django_cotton_components.studio.models import DashboardSpec, SpecRevision

pytestmark = pytest.mark.django_db

panel = Panel("s").path("s").studio().auth(lambda r: r.user.is_authenticated)
urlpatterns = [panel.mount()]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__
    settings.LOGIN_URL = "/accounts/login/"


@pytest.fixture
def studio_user(django_user_model):
    user = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    user.user_permissions.add(Permission.objects.get(codename="use_studio"))
    return user


@pytest.fixture
def spec():
    return DashboardSpec.objects.create(
        slug="article",
        label="Articles",
        model="testapp.Article",
        table={"columns": [{"type": "TextColumn", "name": "title"}], "searchable": True},
        schema={"fields": ["title", "slug"]},
        infolist={},
    )


def test_index_scaffolds_from_a_model(client, urlconf, studio_user):
    client.force_login(studio_user)
    assert client.get("/s/studio/resources/").status_code == 200
    response = client.post("/s/studio/resources/", {"model": "testapp.author"})
    assert response.status_code == 302
    created = DashboardSpec.objects.get(slug="author")
    assert created.model == "testapp.author"
    assert created.table["columns"]  # scaffolder filled it


def test_builder_renders(client, urlconf, studio_user, spec):
    client.force_login(studio_user)
    response = client.get("/s/studio/resources/article/")
    assert response.status_code == 200
    assert b"dccStudioDoc" in response.content
    assert b"res-boot" in response.content


def test_save_columns_and_filters(client, urlconf, studio_user, spec):
    client.force_login(studio_user)
    doc = {
        "columns": [
            {"id": "c0", "type": "TextColumn", "config": {"name": "title", "sortable": True}},
            {"id": "c1", "type": "BadgeColumn", "config": {"name": "status"}},
        ],
        "filters": [
            {"id": "f0", "type": "SelectFilter", "config": {"name": "status"}},
        ],
    }
    response = client.post(
        "/s/studio/resources/article/save/", {"doc": json.dumps(doc), "revision": "0"}
    )
    assert response.status_code == 200
    spec.refresh_from_db()
    assert [c["name"] for c in spec.table["columns"]] == ["title", "status"]
    assert spec.table["filters"][0]["type"] == "SelectFilter"
    assert spec.table["searchable"] is True  # untouched key preserved
    assert spec.revision == 1
    assert SpecRevision.objects.filter(dashboard_spec=spec).count() == 1


def test_save_rejects_unsafe_field_path(client, urlconf, studio_user, spec):
    client.force_login(studio_user)
    doc = {
        "columns": [],
        "filters": [
            {"id": "f0", "type": "Filter", "config": {"name": "x", "field": "author__name__x"}}
        ],
    }
    response = client.post(
        "/s/studio/resources/article/save/", {"doc": json.dumps(doc), "revision": "0"}
    )
    assert response.status_code == 422


def test_stale_revision_conflicts(client, urlconf, studio_user, spec):
    client.force_login(studio_user)
    spec.revision = 3
    spec.save()
    response = client.post(
        "/s/studio/resources/article/save/",
        {"doc": json.dumps({"columns": [], "filters": []}), "revision": "0"},
    )
    assert response.status_code == 409


def test_preview_renders_a_table(client, urlconf, studio_user, spec, article):
    client.force_login(studio_user)
    doc = {
        "columns": [{"id": "c0", "type": "TextColumn", "config": {"name": "title"}}],
        "filters": [],
    }
    response = client.post("/s/studio/resources/article/preview/", {"doc": json.dumps(doc)})
    assert response.status_code == 200
    assert b"Analytical Engine" in response.content
