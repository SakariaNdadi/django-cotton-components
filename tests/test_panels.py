from __future__ import annotations

import pytest
from django.contrib.auth.models import Permission

from django_cotton_components.panels import (
    ChartWidget,
    DashboardPage,
    Panel,
    PanelPage,
    Resource,
    StatWidget,
)
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


class Dash(DashboardPage):
    page_title = "Overview"

    def widgets(self, request):
        return [
            StatWidget.make("Articles", Article.objects.count()).icon("newspaper"),
            ChartWidget.make("By status").data([("Live", 3), ("Draft", 1)]),
        ]


class Reports(PanelPage):
    template_name = "django_cotton_components/panels/dashboard.html"
    slug = "reports"
    nav_label = "Reports"


panel = Panel("admin").path("app").pages([Dash, Reports]).resources([ArticleResource])
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


def test_panelpage_public_export_and_legacy_alias():
    from django_cotton_components.panels import PanelPage as Exported
    from django_cotton_components.panels.pages import PanelPage, _PanelPage

    assert Exported is PanelPage
    assert _PanelPage is PanelPage


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


def test_delete_requires_permission_then_deletes(client, urlconf, staff, author, django_user_model):
    art = Article.objects.create(title="Doomed", slug="doomed", status="draft", author=author)
    client.force_login(staff)  # has view/add/change but NOT delete
    assert client.get(f"/app/article/{art.pk}/delete/").status_code == 403

    staff.user_permissions.add(Permission.objects.get(codename="delete_article"))
    staff = django_user_model.objects.get(pk=staff.pk)  # drop the perm cache
    client.force_login(staff)
    assert client.get(f"/app/article/{art.pk}/delete/").status_code == 200
    resp = client.post(f"/app/article/{art.pk}/delete/")
    assert resp.status_code == 302
    assert not Article.objects.filter(pk=art.pk).exists()


def test_dashboard_page_renders_widgets(client, urlconf, staff):
    client.force_login(staff)
    resp = client.get("/app/")
    assert resp.status_code == 200
    assert b"dcc-widget--stat" in resp.content
    assert b"dcc-widget--chart" in resp.content
    assert b"Overview" in resp.content


def test_widget_fragment_endpoint_returns_content_only(client, urlconf, staff):
    client.force_login(staff)
    resp = client.get("/app/?_dcc_widget=w1", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "dccChart(" in body
    assert "<html" not in body and "dcc-widget--chart" not in body


def test_widget_fragment_unknown_id_is_404(client, urlconf, staff):
    client.force_login(staff)
    resp = client.get("/app/?_dcc_widget=nope", HTTP_HX_REQUEST="true")
    assert resp.status_code == 404


def test_dashboard_marks_auto_refresh_widgets(client, urlconf, staff):
    client.force_login(staff)
    body = client.get("/app/").content.decode()
    assert "_dcc_widget=w0" in body  # StatWidget auto-refreshes
    assert "dcc:refresh from:body" in body


def test_custom_page_routed_and_in_nav(client, rf, urlconf, staff):
    client.force_login(staff)
    assert client.get("/app/reports/").status_code == 200
    request = rf.get("/")
    request.user = staff
    labels = [i["label"] for i in panel.navigation(request)]
    assert "Reports" in labels and "Dashboard" in labels


def test_navigation_lists_permitted_resources(rf, urlconf, staff):
    request = rf.get("/")
    request.user = staff
    nav = panel.navigation(request)
    articles = next(i for i in nav if i["label"] == "Articles")
    assert articles["url"].endswith("/article/")


def test_superuser_bypasses_permissions(client, urlconf, author, django_user_model):
    su = django_user_model.objects.create_superuser("root", "r@x.com", "x")
    client.force_login(su)
    assert client.get("/app/article/new/").status_code == 200
