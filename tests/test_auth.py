"""Login-redirect guards on panel pages."""

from __future__ import annotations

import pytest

from django_control_components.panels import Panel
from django_control_components.panels.guards import login_required, staff_required
from django_control_components.panels.resource import Resource
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


class ArticleResource(Resource):
    model = Article


panel = Panel("auth").path("auth").resources([ArticleResource]).auth(login_required)
urlpatterns = [panel.mount()]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__
    settings.LOGIN_URL = "/accounts/login/"


def test_anonymous_is_redirected_not_403(client, urlconf):
    response = client.get("/auth/article/")
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/?next=/auth/article/")


def test_authenticated_without_permission_gets_403(client, urlconf, django_user_model):
    user = django_user_model.objects.create_user("u", password="x")
    client.force_login(user)
    response = client.get("/auth/article/")
    assert response.status_code == 403


def test_superuser_passes(client, urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    client.force_login(root)
    assert client.get("/auth/article/").status_code == 200


def test_staff_guard_redirects_anonymous():
    from django.test import RequestFactory

    from django_control_components.panels.guards import LoginRequired

    request = RequestFactory().get("/")
    from django.contrib.auth.models import AnonymousUser

    request.user = AnonymousUser()
    with pytest.raises(LoginRequired):
        staff_required(request)


def test_panel_login_url_override():
    p = Panel("x").login_url("/signin/")
    assert p.get_login_url() == "/signin/"


def test_permission_and_group_guards(django_user_model):
    from django.contrib.auth.models import Group
    from django.test import RequestFactory

    from django_control_components.panels.guards import group_required, permission_required

    rf = RequestFactory()
    plain = django_user_model.objects.create_user("g1")
    req = rf.get("/")
    req.user = plain
    assert permission_required("testapp.view_article")(req) is False
    assert group_required("staff")(req) is False

    grp = Group.objects.create(name="staff")
    plain.groups.add(grp)
    plain = django_user_model.objects.get(pk=plain.pk)
    req.user = plain
    assert group_required("staff")(req) is True

    root = django_user_model.objects.create_superuser("g2", "g@x.io", "x")
    req.user = root
    assert group_required("anything")(req) is True
