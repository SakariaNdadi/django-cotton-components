"""studio.home.resolve_home cascade."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from django_cotton_components.panels import Panel
from django_cotton_components.studio.home import resolve_home
from django_cotton_components.studio.models import PanelDashboard, UserPreference

pytestmark = pytest.mark.django_db

panel = Panel("s").path("s").studio()
urlpatterns = [panel.mount()]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__


def _req(user):
    from django.test import RequestFactory

    request = RequestFactory().get("/s/studio/")
    request.user = user
    return request


def test_falls_back_to_panel_index_when_nothing_matches(urlconf, django_user_model):
    user = django_user_model.objects.create_user("u1")
    # no dashboards, no nav, no index page -> "/"
    assert resolve_home(_req(user), panel) == "/"


def test_first_visible_dashboard(urlconf, django_user_model):
    user = django_user_model.objects.create_user("u2")
    PanelDashboard.objects.create(slug="a", widgets=[], is_public=True)
    url = resolve_home(_req(user), panel)
    assert url.endswith("/dash/a/")


def test_group_default_dashboard_wins(urlconf, django_user_model):
    user = django_user_model.objects.create_user("u3")
    group = Group.objects.create(name="ops")
    user.groups.add(group)
    PanelDashboard.objects.create(slug="general", widgets=[], is_public=True)
    special = PanelDashboard.objects.create(slug="ops-board", widgets=[], is_public=True)
    special.default_for_groups.add(group)
    assert resolve_home(_req(user), panel).endswith("/dash/ops-board/")


def test_user_preference_wins(urlconf, django_user_model):
    user = django_user_model.objects.create_user("u4")
    PanelDashboard.objects.create(slug="default", widgets=[], is_public=True)
    PanelDashboard.objects.create(slug="mine", widgets=[], is_public=True)
    UserPreference.objects.create(user=user, home_kind="dashboard", home_target="mine")
    assert resolve_home(_req(user), panel).endswith("/dash/mine/")


def test_superuser_lands_on_a_dashboard_it_can_see(urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    PanelDashboard.objects.create(slug="ops", widgets=[])  # not public, no grants
    assert resolve_home(_req(root), panel).endswith("/dash/ops/")
