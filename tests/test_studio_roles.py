"""Users & Roles — superuser-only access matrix with grant toggles."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import include, path

from django_control_components.panels import Panel
from django_control_components.studio.models import PanelDashboard

pytestmark = pytest.mark.django_db

panel = Panel("s").path("s").studio().auth(lambda r: r.user.is_authenticated)
urlpatterns = [
    panel.mount(),
    path("studio/", include("django_control_components.studio.urls")),
]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__
    settings.LOGIN_URL = "/accounts/login/"


@pytest.fixture
def dashboard():
    return PanelDashboard.objects.create(slug="ops", label="Ops", widgets=[])


def test_non_superuser_studio_user_cannot_open_roles(client, urlconf, django_user_model):
    user = django_user_model.objects.create_user("editor", password="x")
    user.user_permissions.add(Permission.objects.get(codename="use_studio"))
    client.force_login(django_user_model.objects.get(pk=user.pk))
    assert client.get("/studio/roles/").status_code == 403


def test_superuser_sees_the_matrix(client, urlconf, django_user_model, dashboard):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    Group.objects.create(name="Managers")
    client.force_login(root)
    response = client.get("/studio/roles/")
    assert response.status_code == 200
    assert b"Managers" in response.content
    assert b"Ops" in response.content


def test_grant_and_revoke_a_group(client, urlconf, django_user_model, dashboard):
    root = django_user_model.objects.create_superuser("root2", "r2@x.io", "x")
    group = Group.objects.create(name="Managers")
    client.force_login(root)

    client.post(
        "/studio/roles/",
        {"kind": "dashboard", "pk": dashboard.pk, "group": group.pk, "action": "grant"},
    )
    assert dashboard.groups.filter(pk=group.pk).exists()

    client.post(
        "/studio/roles/",
        {"kind": "dashboard", "pk": dashboard.pk, "group": group.pk, "action": "revoke"},
    )
    assert not dashboard.groups.filter(pk=group.pk).exists()


def test_toggle_public(client, urlconf, django_user_model, dashboard):
    root = django_user_model.objects.create_superuser("root3", "r3@x.io", "x")
    client.force_login(root)
    client.post(
        "/studio/roles/",
        {"kind": "dashboard", "pk": dashboard.pk, "action": "toggle_public"},
    )
    dashboard.refresh_from_db()
    assert dashboard.is_public is True
