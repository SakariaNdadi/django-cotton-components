"""Phase 4c: request-time resolution of Page rows behind a catch-all.

``dcc_pages("site")`` for public pages, the panel ``p/`` catch-all for in-app
pages, and the rule that a page the visitor may not see 404s rather than 403s.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import include, path

from django_control_components.panels import Panel
from django_control_components.studio.models import Page, Visibility
from django_control_components.studio.routing import dcc_pages

pytestmark = pytest.mark.django_db

panel = Panel("s").path("s").studio().auth(lambda r: True)
urlpatterns = [
    panel.mount(),
    path("studio/", include("django_control_components.studio.urls")),
    path("", include(dcc_pages("site"))),
]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__
    settings.LOGIN_URL = "/accounts/login/"


def _grid(text_perms=None):
    node = {"type": "Grid", "props": {}, "slots": {"default": []}}
    return node


# -- public site pages ---------------------------------------------


def test_public_site_page_renders_for_anyone(client, urlconf):
    Page.objects.create(
        mount="site",
        route="about",
        title="About Us",
        visibility=Visibility.PUBLIC,
        tree=_grid(),
    )
    response = client.get("/about")
    assert response.status_code == 200
    assert b"About Us" in response.content


def test_site_index_route_is_empty_string(client, urlconf):
    Page.objects.create(
        mount="site", route="", title="Home", visibility=Visibility.PUBLIC, tree=_grid()
    )
    assert client.get("/").status_code == 200


def test_missing_site_page_is_404(client, urlconf):
    assert client.get("/nope").status_code == 404


def test_restricted_site_page_404s_for_anonymous(client, urlconf):
    Page.objects.create(
        mount="site", route="secret", title="Secret", visibility=Visibility.RESTRICTED, tree=_grid()
    )
    assert client.get("/secret").status_code == 404  # not 403 — existence must not leak


def test_restricted_site_page_renders_for_a_granted_user(client, urlconf, django_user_model):
    group = Group.objects.create(name="staff")
    page = Page.objects.create(
        mount="site", route="secret", title="Secret", visibility=Visibility.RESTRICTED, tree=_grid()
    )
    page.groups.add(group)
    user = django_user_model.objects.create_user("u", password="x")
    user.groups.add(group)
    client.force_login(django_user_model.objects.get(pk=user.pk))
    assert client.get("/secret").status_code == 200


def test_disabled_page_is_404(client, urlconf):
    Page.objects.create(
        mount="site",
        route="draft",
        title="Draft",
        visibility=Visibility.PUBLIC,
        is_enabled=False,
        tree=_grid(),
    )
    assert client.get("/draft").status_code == 404


# -- in-panel pages ----------------------------------------------


def test_panel_page_served_under_the_p_prefix(client, urlconf):
    Page.objects.create(
        mount="panel",
        panel="s",
        route="welcome",
        title="Welcome",
        visibility=Visibility.PUBLIC,
        tree=_grid(),
    )
    response = client.get("/s/p/welcome")
    assert response.status_code == 200
    assert b"Welcome" in response.content


def test_panel_page_catchall_does_not_shadow_a_resource(client, urlconf):
    # nothing at /s/p/ registered as a Page -> 404, and the panel index still works
    assert client.get("/s/p/anything").status_code == 404


def test_panel_page_for_the_wrong_panel_is_404(client, urlconf):
    Page.objects.create(
        mount="panel",
        panel="other",
        route="x",
        title="X",
        visibility=Visibility.PUBLIC,
        tree=_grid(),
    )
    assert client.get("/s/p/x").status_code == 404


def test_dcc_pages_rejects_non_site_mount():
    with pytest.raises(ValueError, match="only the public 'site'"):
        dcc_pages("panel")
