"""The AccessControlled three-state visibility mixin and the studio gate."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, Group, Permission

from django_control_components.studio.access import can_use_studio, require_studio
from django_control_components.studio.models import PanelDashboard, Visibility, visible_queryset

pytestmark = pytest.mark.django_db


@pytest.fixture
def dashboard():
    return PanelDashboard.objects.create(slug="ops", label="Ops", widgets=[])


def _req(user):
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.user = user
    return request


def test_restricted_is_the_default_and_is_invisible_without_a_grant(dashboard, django_user_model):
    assert dashboard.visibility == Visibility.RESTRICTED
    user = django_user_model.objects.create_user("u1")
    assert dashboard.is_visible_to(user) is False


def test_public_includes_signed_out_visitors(dashboard):
    dashboard.visibility = Visibility.PUBLIC
    dashboard.save()
    assert dashboard.is_visible_to(AnonymousUser()) is True
    assert dashboard.is_visible_to(None) is True


def test_authenticated_covers_any_signed_in_user_but_not_anonymous(dashboard, django_user_model):
    dashboard.visibility = Visibility.AUTHENTICATED
    dashboard.save()
    assert dashboard.is_visible_to(django_user_model.objects.create_user("u2")) is True
    assert dashboard.is_visible_to(AnonymousUser()) is False


def test_restricted_direct_user_grant(dashboard, django_user_model):
    user = django_user_model.objects.create_user("u3")
    dashboard.users.add(user)
    assert dashboard.is_visible_to(user) is True


def test_restricted_group_grant(dashboard, django_user_model):
    user = django_user_model.objects.create_user("u4")
    group = Group.objects.create(name="ops-team")
    user.groups.add(group)
    dashboard.groups.add(group)
    assert dashboard.is_visible_to(user) is True


def test_restricted_required_permission_is_a_deny_gate_before_the_grant(
    dashboard, django_user_model
):
    group = Group.objects.create(name="ops")
    dashboard.groups.add(group)
    dashboard.required_permission = "dcc_studio.use_studio"
    dashboard.save()
    user = django_user_model.objects.create_user("u5")
    user.groups.add(group)
    assert dashboard.is_visible_to(user) is False  # in the group, but lacks the perm
    user.user_permissions.add(Permission.objects.get(codename="use_studio"))
    user = django_user_model.objects.get(pk=user.pk)
    assert dashboard.is_visible_to(user) is True


def test_superuser_sees_everything(dashboard, django_user_model):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    assert dashboard.is_visible_to(root) is True


def test_visible_queryset_matches_is_visible_to_for_anonymous(django_user_model):
    PanelDashboard.objects.create(slug="pub", widgets=[], visibility=Visibility.PUBLIC)
    PanelDashboard.objects.create(slug="auth", widgets=[], visibility=Visibility.AUTHENTICATED)
    PanelDashboard.objects.create(slug="restricted", widgets=[])
    qs = visible_queryset(PanelDashboard.objects.all(), AnonymousUser())
    assert set(qs.values_list("slug", flat=True)) == {"pub"}


def test_visible_queryset_for_a_plain_user(django_user_model):
    PanelDashboard.objects.create(slug="pub", widgets=[], visibility=Visibility.PUBLIC)
    PanelDashboard.objects.create(slug="auth", widgets=[], visibility=Visibility.AUTHENTICATED)
    PanelDashboard.objects.create(slug="restricted", widgets=[])
    user = django_user_model.objects.create_user("u6")
    qs = visible_queryset(PanelDashboard.objects.all(), user)
    assert set(qs.values_list("slug", flat=True)) == {"pub", "auth"}


def test_studio_permission_gate(django_user_model):
    plain = django_user_model.objects.create_user("plain")
    assert can_use_studio(_req(plain)) is False
    plain.user_permissions.add(Permission.objects.get(codename="use_studio"))
    plain = django_user_model.objects.get(pk=plain.pk)
    assert can_use_studio(_req(plain)) is True


def test_require_studio_raises_login_required_for_anonymous():
    from django_control_components.panels.guards import LoginRequired

    with pytest.raises(LoginRequired):
        require_studio(_req(AnonymousUser()))
