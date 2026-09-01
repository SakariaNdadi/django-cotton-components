"""The studio as a standalone mount + its Django-admin entry (Phase 1)."""

from __future__ import annotations

import pytest
from django.contrib import admin as django_admin
from django.contrib.auth.models import Permission
from django.urls import include, path, reverse

from django_control_components.panels import Panel
from django_control_components.panels.resource import Resource
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


class ArticleResource(Resource):
    model = Article


panel = Panel("shop").path("shop").resources([ArticleResource]).studio()
plain_panel = Panel("plain").path("plain").resources([ArticleResource])  # no .studio()

urlpatterns = [
    path("admin/", django_admin.site.urls),
    path("studio/", include("django_control_components.studio.urls")),
    panel.mount(),
    plain_panel.mount(),
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


def test_namespace_reverses_flat():
    assert reverse("dcc_studio:home") == "/studio/"
    assert reverse("dcc_studio:dashboards") == "/studio/dashboards/"
    assert reverse("dcc_studio:nav", args=["shop"]) == "/studio/nav/shop/"


def test_panel_no_longer_mounts_studio(urlconf):
    from django.urls import NoReverseMatch

    with pytest.raises(NoReverseMatch):
        reverse("dcc-panel-shop:studio-home")


def test_hub_lists_only_studio_enabled_panels(client, urlconf, studio_user):
    client.force_login(studio_user)
    body = client.get("/studio/").content
    assert b"/studio/nav/shop/" in body
    assert b"/studio/nav/plain/" not in body


def test_nav_builder_404s_for_non_studio_panel(client, urlconf, studio_user):
    client.force_login(studio_user)
    assert client.get("/studio/nav/plain/").status_code == 404
    assert client.get("/studio/nav/ghost/").status_code == 404
    assert client.get("/studio/nav/shop/").status_code == 200


def test_anonymous_redirected_to_login(client, urlconf):
    r = client.get("/studio/")
    assert r.status_code == 302
    assert "/accounts/login/" in r["Location"]


def test_admin_entry_visible_and_redirects(client, urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    client.force_login(root)
    index = client.get("/admin/")
    assert b"/admin/dcc_studio/studioentry/" in index.content
    entry = client.get("/admin/dcc_studio/studioentry/")
    assert entry.status_code == 302
    assert entry["Location"] == "/studio/"


def test_admin_entry_hidden_without_use_studio(client, urlconf, django_user_model):
    staff = django_user_model.objects.create_user("staff", password="x", is_staff=True)
    client.force_login(staff)
    index = client.get("/admin/")
    assert b"studioentry" not in index.content
