"""Phase 7: ACTIONS_DEFAULT_DENY, the required_permission Python re-filter,
and RolesView reaching the users / required_permission fields."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory
from django.urls import include, path

from django_control_components.actions.action import Action
from django_control_components.panels import Panel
from django_control_components.studio.models import DashboardSpec, Visibility, visible_list

pytestmark = pytest.mark.django_db


def _req(user=None):
    request = RequestFactory().post("/x/")
    request.user = user
    return request


class _User:
    is_authenticated = True
    is_superuser = False

    def has_perm(self, perm, obj=None):
        return False


def test_action_without_a_rule_is_allowed_by_default():
    assert Action.make("touch").is_authorized(_req(_User())) is True


def test_action_without_a_rule_is_denied_when_actions_default_deny(settings):
    settings.DCC = {"ACTIONS_DEFAULT_DENY": True}
    assert Action.make("touch").is_authorized(_req(_User())) is False


def test_an_explicit_rule_still_wins_under_default_deny(settings):
    settings.DCC = {"ACTIONS_DEFAULT_DENY": True}
    action = Action.make("touch").authorize(lambda user: True)
    assert action.is_authorized(_req(_User())) is True


# -- required_permission Python re-filter ---------------------------


def test_visible_list_drops_a_restricted_row_with_an_unmet_permission(django_user_model):
    user = django_user_model.objects.create_user("u")
    group = Group.objects.create(name="g")
    user.groups.add(group)

    open_row = DashboardSpec.objects.create(
        slug="open", model="testapp.Article", visibility=Visibility.RESTRICTED
    )
    open_row.groups.add(group)
    gated = DashboardSpec.objects.create(
        slug="gated",
        model="testapp.Article",
        visibility=Visibility.RESTRICTED,
        required_permission="testapp.view_article",
    )
    gated.groups.add(group)

    user = django_user_model.objects.get(pk=user.pk)
    visible = visible_list(DashboardSpec.objects.all(), user)
    assert open_row in visible
    assert gated not in visible

    user.user_permissions.add(Permission.objects.get(codename="view_article"))
    user = django_user_model.objects.get(pk=user.pk)
    assert gated in visible_list(DashboardSpec.objects.all(), user)


# -- RolesView reaches users / required_permission -----------------

panel = Panel("s").path("s").studio().auth(lambda r: True)
urlpatterns = [panel.mount(), path("studio/", include("django_control_components.studio.urls"))]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__
    settings.LOGIN_URL = "/accounts/login/"


def test_roles_view_sets_required_permission_and_users(client, urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    alice = django_user_model.objects.create_user("alice")
    spec = DashboardSpec.objects.create(slug="ops", model="testapp.Article")
    client.force_login(root)

    client.post(
        "/studio/roles/",
        {
            "kind": "spec",
            "pk": spec.pk,
            "action": "set_permission",
            "required_permission": "testapp.view_article",
        },
    )
    client.post(
        "/studio/roles/",
        {"kind": "spec", "pk": spec.pk, "action": "set_users", "usernames": "alice"},
    )
    spec.refresh_from_db()
    assert spec.required_permission == "testapp.view_article"
    assert list(spec.users.all()) == [alice]
