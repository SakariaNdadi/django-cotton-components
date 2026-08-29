"""The dashboard builder: index/create, GET render, revision-guarded save,
preview, SpecRevision snapshots."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Permission

from django_control_components.panels import Panel
from django_control_components.studio.models import PanelDashboard, SpecRevision

pytestmark = pytest.mark.django_db


panel = Panel("s").path("s").studio().auth(lambda r: r.user.is_authenticated)
urlpatterns = [panel.mount()]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__
    settings.LOGIN_URL = "/accounts/login/"
    settings.DCC = {"STUDIO_MODELS": ["testapp.Article"]}


@pytest.fixture
def studio_user(django_user_model):
    user = django_user_model.objects.create_user("editor", password="x")
    user.user_permissions.add(Permission.objects.get(codename="use_studio"))
    return django_user_model.objects.get(pk=user.pk)


@pytest.fixture
def dashboard():
    return PanelDashboard.objects.create(slug="ops", label="Ops", widgets=[])


def test_index_lists_and_creates(client, urlconf, studio_user):
    client.force_login(studio_user)
    assert client.get("/s/studio/dashboards/").status_code == 200
    response = client.post("/s/studio/dashboards/", {"label": "Revenue"})
    assert response.status_code == 302
    assert PanelDashboard.objects.filter(slug="revenue").exists()


def test_builder_renders(client, urlconf, studio_user, dashboard):
    client.force_login(studio_user)
    response = client.get("/s/studio/dashboards/ops/")
    assert response.status_code == 200
    assert b"dccStudioDoc" in response.content
    assert b"StatWidget" in response.content  # a palette entry


def test_save_writes_widgets_and_a_revision(client, urlconf, studio_user, dashboard):
    client.force_login(studio_user)
    doc = {"items": [{"id": "w0", "type": "StatWidget", "config": {"name": "Articles"}}]}
    response = client.post(
        "/s/studio/dashboards/ops/save/", {"doc": json.dumps(doc), "revision": "0"}
    )
    assert response.status_code == 200
    assert response.json()["revision"] == 1

    dashboard.refresh_from_db()
    assert dashboard.widgets[0]["type"] == "StatWidget"
    assert dashboard.revision == 1
    assert SpecRevision.objects.filter(panel_dashboard=dashboard).count() == 1


def test_stale_revision_conflicts(client, urlconf, studio_user, dashboard):
    client.force_login(studio_user)
    dashboard.revision = 5
    dashboard.save()
    response = client.post(
        "/s/studio/dashboards/ops/save/", {"doc": json.dumps({"items": []}), "revision": "0"}
    )
    assert response.status_code == 409
    assert response.json()["revision"] == 5


def test_save_rejects_unknown_widget_type(client, urlconf, studio_user, dashboard):
    client.force_login(studio_user)
    doc = {"items": [{"id": "w0", "type": "TeleportWidget", "config": {}}]}
    response = client.post(
        "/s/studio/dashboards/ops/save/", {"doc": json.dumps(doc), "revision": "0"}
    )
    assert response.status_code == 422


def test_preview_renders_widgets(client, urlconf, studio_user, dashboard):
    client.force_login(studio_user)
    doc = {"items": [{"id": "w0", "type": "StatWidget", "config": {"name": "Count"}}]}
    response = client.post("/s/studio/dashboards/ops/preview/", {"doc": json.dumps(doc)})
    assert response.status_code == 200
    assert b"dcc-widget" in response.content


def test_query_widget_round_trips_through_the_builder(client, urlconf, studio_user, dashboard):
    client.force_login(studio_user)
    doc = {
        "items": [
            {
                "id": "w0",
                "type": "StatWidget",
                "config": {
                    "name": "Articles",
                    "query": {"model": "testapp.Article", "aggregate": "count"},
                },
            }
        ]
    }
    response = client.post(
        "/s/studio/dashboards/ops/save/", {"doc": json.dumps(doc), "revision": "0"}
    )
    assert response.status_code == 200
    dashboard.refresh_from_db()
    assert dashboard.widgets[0]["config"]["query"]["model"] == "testapp.Article"
