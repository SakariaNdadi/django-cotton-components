"""Phase 4d: the page builder views, the studio hub entry, the nav ``page``
target kind and the ``Page.is_home`` extension to ``resolve_home``."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from django.urls import include, path

from django_control_components.panels import Panel
from django_control_components.panels.nav import build_nav
from django_control_components.studio.home import resolve_home
from django_control_components.studio.models import NavItem, Page, SpecRevision, Visibility

pytestmark = pytest.mark.django_db

panel = Panel("s").path("s").studio().auth(lambda r: True)
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


def _grid():
    return {"type": "Grid", "props": {}, "slots": {"default": []}}


# -- builder views ------------------------------------------------


def test_index_lists_and_creates(client, urlconf, studio_user):
    client.force_login(studio_user)
    assert client.get("/studio/pages/").status_code == 200
    response = client.post("/studio/pages/", {"title": "About", "route": "about", "mount": "site"})
    assert response.status_code == 302
    page = Page.objects.get(route="about")
    assert response["Location"] == f"/studio/pages/{page.pk}/"


def test_create_rejects_a_duplicate_route(client, urlconf, studio_user):
    Page.objects.create(title="A", route="about", mount="site")
    client.force_login(studio_user)
    response = client.post("/studio/pages/", {"title": "B", "route": "about", "mount": "site"})
    assert response.status_code == 200
    assert b"already exists" in response.content
    assert Page.objects.filter(route="about").count() == 1


def test_builder_renders_with_boot_json(client, urlconf, studio_user):
    page = Page.objects.create(title="Home", route="", tree=_grid())
    client.force_login(studio_user)
    response = client.get(f"/studio/pages/{page.pk}/")
    assert response.status_code == 200
    assert b"page-boot" in response.content


def test_save_is_revision_guarded(client, urlconf, studio_user):
    page = Page.objects.create(title="Home", route="", tree={})
    client.force_login(studio_user)
    body = {"doc": json.dumps({"root": _grid()}), "revision": 0}
    ok = client.post(f"/studio/pages/{page.pk}/save/", body)
    assert ok.status_code == 200 and ok.json()["revision"] == 1
    page.refresh_from_db()
    assert page.tree["type"] == "Grid"
    assert SpecRevision.objects.filter(page=page).count() == 1

    stale = client.post(
        f"/studio/pages/{page.pk}/save/", {"doc": json.dumps({"root": {}}), "revision": 0}
    )
    assert stale.status_code == 409
    assert stale.json()["revision"] == 1


def test_save_rejects_an_invalid_tree(client, urlconf, studio_user):
    page = Page.objects.create(title="Home", route="", tree={})
    client.force_login(studio_user)
    body = {"doc": json.dumps({"root": {"type": "NoSuchBlock", "slots": {}}}), "revision": 0}
    response = client.post(f"/studio/pages/{page.pk}/save/", body)
    assert response.status_code == 422


def test_preview_renders_the_tree(client, urlconf, studio_user):
    page = Page.objects.create(title="Home", route="", tree={})
    client.force_login(studio_user)
    response = client.post(
        f"/studio/pages/{page.pk}/preview/", {"doc": json.dumps({"root": _grid()}), "revision": 0}
    )
    assert response.status_code == 200
    assert b"dcc-grid" in response.content or b"--dcc-cols" in response.content


def test_hub_shows_the_pages_card(client, urlconf, studio_user):
    client.force_login(studio_user)
    response = client.get("/studio/")
    assert b"/studio/pages/" in response.content


# -- nav page target kind ---------------------------------------


def _req(user):
    request = RequestFactory().get("/s/")
    request.user = user
    return request


def test_nav_page_kind_resolves_to_the_panel_page_url(urlconf, django_user_model):
    user = django_user_model.objects.create_user("u")
    Page.objects.create(
        mount="panel",
        panel="s",
        route="welcome",
        title="Welcome",
        visibility=Visibility.PUBLIC,
        tree=_grid(),
    )
    NavItem.objects.create(
        panel="s",
        label="Welcome",
        target_kind=NavItem.Kind.PAGE,
        target="welcome",
        visibility=Visibility.PUBLIC,
    )
    nodes = build_nav(panel, _req(user))
    assert any(n.url == "/s/p/welcome" for n in nodes)


def test_nav_page_kind_dropped_when_page_not_visible(urlconf, django_user_model):
    user = django_user_model.objects.create_user("u")
    Page.objects.create(
        mount="panel",
        panel="s",
        route="secret",
        title="Secret",
        visibility=Visibility.RESTRICTED,
        tree=_grid(),
    )
    NavItem.objects.create(
        panel="s",
        label="Secret",
        target_kind=NavItem.Kind.PAGE,
        target="secret",
        visibility=Visibility.PUBLIC,
    )
    nodes = build_nav(panel, _req(user))
    assert not any("secret" in n.url for n in nodes)


# -- resolve_home ---------------------------------------------


def test_resolve_home_prefers_an_is_home_page(urlconf, django_user_model):
    user = django_user_model.objects.create_user("u")
    Page.objects.create(
        mount="panel",
        panel="s",
        route="dashboard",
        title="Dash",
        is_home=True,
        visibility=Visibility.PUBLIC,
        tree=_grid(),
    )
    assert resolve_home(_req(user), panel) == "/s/p/dashboard"
