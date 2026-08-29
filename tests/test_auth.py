"""Login-redirect guards on panel pages."""

from __future__ import annotations

import pytest

from django_cotton_components.panels import Panel
from django_cotton_components.panels.guards import login_required, staff_required
from django_cotton_components.panels.resource import Resource
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

    from django_cotton_components.panels.guards import LoginRequired

    request = RequestFactory().get("/")
    from django.contrib.auth.models import AnonymousUser

    request.user = AnonymousUser()
    with pytest.raises(LoginRequired):
        staff_required(request)


def test_panel_login_url_override():
    p = Panel("x").login_url("/signin/")
    assert p.get_login_url() == "/signin/"
