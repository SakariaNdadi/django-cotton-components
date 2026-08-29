"""build_nav — merging code and stored navigation into one tree."""

from __future__ import annotations

import pytest

from django_control_components.panels import Panel
from django_control_components.panels.nav import build_nav
from django_control_components.panels.resource import Resource
from django_control_components.studio.models import NavItem
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


class ArticleResource(Resource):
    model = Article
    navigation_group = "Content"


panel = Panel("nav").path("nav").resources([ArticleResource])
urlpatterns = [panel.mount()]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__


def _req(path, user):
    from django.test import RequestFactory

    request = RequestFactory().get(path)
    request.user = user
    return request


def test_code_resource_is_grouped(urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    tree = build_nav(panel, _req("/nav/", root))
    groups = [n for n in tree if n.is_heading]
    assert any(g.label == "Content" for g in groups)
    content = next(g for g in tree if g.label == "Content")
    assert any(c.label.lower().startswith("article") for c in content.children)


def test_navitem_url_target_and_active_state(urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("root2", "r2@x.io", "x")
    NavItem.objects.create(
        panel="nav", label="Docs", target_kind=NavItem.Kind.URL, target="/docs/", is_public=True
    )
    tree = build_nav(panel, _req("/docs/sub/", root))
    docs = next(n for n in tree if n.label == "Docs")
    assert docs.url == "/docs/"
    assert docs.active is True


def test_navitem_rejects_javascript_url():
    from django.core.exceptions import ValidationError

    item = NavItem(
        panel="nav", label="x", target_kind=NavItem.Kind.URL, target="javascript:alert(1)"
    )
    with pytest.raises(ValidationError):
        item.full_clean()


def test_navitem_hidden_when_not_visible(urlconf, django_user_model):
    NavItem.objects.create(
        panel="nav", label="Secret", target_kind=NavItem.Kind.URL, target="/secret/"
    )
    user = django_user_model.objects.create_user("plain")
    labels = {n.label for n in build_nav(panel, _req("/nav/", user))}
    assert "Secret" not in labels


def test_navitem_resource_target_resolves(urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("r3", "r3@x.io", "x")
    NavItem.objects.create(
        panel="nav",
        label="Articles",
        target_kind=NavItem.Kind.RESOURCE,
        target="article",
        is_public=True,
    )
    labels = {n.label: n for n in build_nav(panel, _req("/nav/", root))}
    assert "/nav/article/" in labels["Articles"].url


def test_navitem_dead_target_is_dropped(urlconf, django_user_model):
    root = django_user_model.objects.create_superuser("r4", "r4@x.io", "x")
    NavItem.objects.create(
        panel="nav",
        label="Ghost",
        target_kind=NavItem.Kind.SPEC,
        target="does-not-exist",
        is_public=True,
    )
    assert "Ghost" not in {n.label for n in build_nav(panel, _req("/nav/", root))}


def test_navitem_nesting_capped_at_two_levels():
    from django.core.exceptions import ValidationError

    a = NavItem.objects.create(panel="nav", label="A", target_kind=NavItem.Kind.GROUP)
    b = NavItem.objects.create(panel="nav", label="B", target_kind=NavItem.Kind.GROUP, parent=a)
    c = NavItem.objects.create(panel="nav", label="C", target_kind=NavItem.Kind.GROUP, parent=b)
    d = NavItem(panel="nav", label="D", target_kind=NavItem.Kind.URL, target="/d/", parent=c)
    with pytest.raises(ValidationError):
        d.full_clean()
