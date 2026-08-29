"""The AccessControlled visibility mixin and the studio permission gate."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, Permission

from django_cotton_components.studio.access import can_use_studio, require_studio
from django_cotton_components.studio.models import PanelDashboard, visible_queryset

pytestmark = pytest.mark.django_db


@pytest.fixture
def dashboard():
    return PanelDashboard.objects.create(slug="ops", label="Ops", widgets=[])


def _req(user):
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.user = user
    return request


def test_ungranted_row_is_invisible(dashboard, django_user_model):
    user = django_user_model.objects.create_user("u1")
    assert dashboard.is_visible_to(user) is False


def test_public_row_visible_to_any_authenticated_user(dashboard, django_user_model):
    dashboard.is_public = True
    dashboard.save()
    user = django_user_model.objects.create_user("u2")
    assert dashboard.is_visible_to(user) is True
    assert dashboard.is_visible_to(None) is False


def test_direct_user_grant(dashboard, django_user_model):
    user = django_user_model.objects.create_user("u3")
    dashboard.users.add(user)
    assert dashboard.is_visible_to(user) is True


def test_group_grant(dashboard, django_user_model):
    user = django_user_model.objects.create_user("u4")
    group = Group.objects.create(name="ops-team")
    user.groups.add(group)
    dashboard.groups.add(group)
    assert dashboard.is_visible_to(user) is True


def test_required_permission_gates_even_a_public_row(dashboard, django_user_model):
    dashboard.is_public = True
    dashboard.required_permission = "dcc_studio.use_studio"
    dashboard.save()
    user = django_user_model.objects.create_user("u5")
    assert dashboard.is_visible_to(user) is False
    user.user_permissions.add(Permission.objects.get(codename="use_studio"))
    user = django_user_model.objects.get(pk=user.pk)
    assert dashboard.is_visible_to(user) is True


def test_superuser_sees_everything(dashboard, django_user_model):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    assert dashboard.is_visible_to(root) is True


def test_visible_queryset_matches_is_visible_to(django_user_model):
    PanelDashboard.objects.create(slug="a", widgets=[], is_public=True)
    PanelDashboard.objects.create(slug="b", widgets=[])
    user = django_user_model.objects.create_user("u6")
    qs = visible_queryset(PanelDashboard.objects.all(), user)
    assert set(qs.values_list("slug", flat=True)) == {"a"}


def test_studio_permission_gate(django_user_model):
    plain = django_user_model.objects.create_user("plain")
    assert can_use_studio(_req(plain)) is False
    plain.user_permissions.add(Permission.objects.get(codename="use_studio"))
    plain = django_user_model.objects.get(pk=plain.pk)
    assert can_use_studio(_req(plain)) is True


def test_require_studio_raises_login_required_for_anonymous():
    from django.contrib.auth.models import AnonymousUser

    from django_cotton_components.panels.guards import LoginRequired

    with pytest.raises(LoginRequired):
        require_studio(_req(AnonymousUser()))
