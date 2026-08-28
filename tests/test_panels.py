from __future__ import annotations

import pytest
from django.contrib.auth.models import Permission

from django_cotton_components.panels import Panel, Resource
from django_cotton_components.schemas import Schema, Section, TextInput
from tests.testapp.forms import ArticleForm
from tests.testapp.models import Article, Author

pytestmark = pytest.mark.django_db


class ArticleResource(Resource):
    model = Article
    navigation_icon = "doc"

    @classmethod
    def build_schema(cls, *, request):
        return (
            Schema.make()
            .form(ArticleForm)
            .schema(
                [Section.make("Main").schema([TextInput.make("title"), TextInput.make("slug")])]
            )
        )


panel = Panel("admin").path("app").resources([ArticleResource])
panel.auth(lambda r: r.user.is_authenticated)

urlpatterns = [panel.mount()]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = "tests.test_panels"


@pytest.fixture
def staff(django_user_model):
    user = django_user_model.objects.create_user("bob", password="x")
    for codename in ("view_article", "add_article", "change_article"):
        user.user_permissions.add(Permission.objects.get(codename=codename))
    return user


@pytest.fixture
def author():
    return Author.objects.create(name="Ada")


def test_anonymous_is_denied(client, urlconf):
    assert client.get("/app/article/").status_code in (403, 302)


def test_list_page_renders_table(client, urlconf, staff, author):
    Article.objects.create(title="Hi", slug="hi", status="draft", author=author)
    client.force_login(staff)
    resp = client.get("/app/article/")
    assert resp.status_code == 200
    assert b"dcc-table" in resp.content
    assert b"Hi" in resp.content


def test_permission_gates_create(client, urlconf, author, django_user_model):
    viewer = django_user_model.objects.create_user("v", password="x")
    viewer.user_permissions.add(Permission.objects.get(codename="view_article"))
    client.force_login(viewer)
    assert client.get("/app/article/new/").status_code == 403


def test_create_via_schema_form(client, urlconf, staff, author):
    client.force_login(staff)
    n0 = Article.objects.count()
    resp = client.post(
        "/app/article/new/",
        {
            "title": "Fresh",
            "slug": "fresh",
            "status": "draft",
            "author": author.pk,
        },
    )
    assert resp.status_code == 302
    assert Article.objects.count() == n0 + 1


def test_view_page_infolist(client, urlconf, staff, author):
    art = Article.objects.create(title="Shown", slug="shown", status="live", author=author)
    client.force_login(staff)
    resp = client.get(f"/app/article/{art.pk}/")
    assert resp.status_code == 200
    assert b"Shown" in resp.content
    assert b"dcc-infolist" in resp.content


def test_navigation_lists_permitted_resources(rf, urlconf, staff):
    request = rf.get("/")
    request.user = staff
    nav = panel.navigation(request)
    assert nav[0]["label"] == "Articles"
    assert nav[0]["url"].endswith("/article/")


def test_superuser_bypasses_permissions(client, urlconf, author, django_user_model):
    su = django_user_model.objects.create_superuser("root", "r@x.com", "x")
    client.force_login(su)
    assert client.get("/app/article/new/").status_code == 200
