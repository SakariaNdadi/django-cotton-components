from __future__ import annotations

import pytest
from django.template import Context, Template
from django.test import RequestFactory
from django.views.generic import CreateView

from django_cotton_components.mixins import SchemaFormMixin
from django_cotton_components.schemas import Schema, Section, TextInput
from tests.testapp.forms import ArticleForm
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


def _schema() -> Schema:
    return (
        Schema.make()
        .form(ArticleForm)
        .schema([Section.make("Main").schema([TextInput.make("title"), TextInput.make("slug")])])
    )


def test_dcc_assets_emits_css_and_js():
    out = Template("{% load dcc_tags %}{% dcc_assets %}").render(Context())
    assert "dcc/dcc.css" in out
    assert "dcc/dcc.js" in out
    assert "alpinejs" in out
    assert "htmx" in out


def test_dcc_assets_can_skip_alpine():
    out = Template("{% load dcc_tags %}{% dcc_assets alpine=False %}").render(Context())
    assert "alpinejs" not in out


def test_dcc_assets_can_skip_htmx():
    out = Template("{% load dcc_tags %}{% dcc_assets htmx=False %}").render(Context())
    assert "htmx" not in out


def test_dcc_form_tag_renders_form_with_csrf(rf):
    request = rf.get("/")
    tpl = Template("{% load dcc_tags %}{% dcc_form schema %}")
    out = tpl.render(Context({"schema": _schema(), "request": request, "form": ArticleForm()}))
    assert "<form" in out
    assert "csrfmiddlewaretoken" in out


def test_dcc_render_tag(rf):
    request = rf.get("/")
    tpl = Template("{% load dcc_tags %}{% dcc_render field %}")
    out = tpl.render(Context({"field": TextInput.make("title"), "request": request}))
    assert 'name="title"' in out


def test_get_field_errors_is_deprecated():
    form = ArticleForm(data={})
    form.is_valid()
    with pytest.warns(DeprecationWarning):
        Template("{% load dcc_tags %}{% get_field_errors form 'title' %}").render(
            Context({"form": form})
        )


class _ArticleCreate(SchemaFormMixin, CreateView):
    model = Article
    template_name = "cotton/dcc/button.html"  # any template; we only test context/form_valid
    fields: list[str] = []
    success_url = "/"

    def get_schema(self):
        return _schema()


def test_mixin_supplies_schema_html():
    view = _ArticleCreate()
    view.request = RequestFactory().get("/")
    view.object = None
    ctx = view.get_context_data(form=ArticleForm())
    assert "dcc-form" in str(ctx["schema_html"])
    assert ctx["schema"] is not None


def test_mixin_uses_schema_form_class():
    view = _ArticleCreate()
    assert view.get_form_class() is ArticleForm
