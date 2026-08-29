from __future__ import annotations

import pytest

from django_control_components.core.exceptions import SchemaError
from django_control_components.schemas import (
    Checkbox,
    Schema,
    Section,
    Select,
    Textarea,
    TextInput,
    Toggle,
)
from tests.testapp.forms import ArticleForm
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


def make_schema() -> Schema:
    return (
        Schema.make()
        .form(ArticleForm)
        .schema(
            [
                Section.make("Content")
                .columns(2)
                .schema(
                    [
                        TextInput.make("title").required(),
                        TextInput.make("slug"),
                        Textarea.make("body"),
                        Select.make("status"),
                        Select.make("author"),
                        Checkbox.make("featured"),
                    ]
                ),
            ]
        )
    )


def test_renders_bound_form(soup):
    schema = make_schema()
    html = schema.render(form=ArticleForm())
    doc = soup(str(html))
    assert doc.select_one('input[name="title"][required]')
    assert doc.select_one('textarea[name="body"]')
    # native select present and correctly named
    assert doc.select_one('select[name="status"]')
    assert doc.select_one('select[name="author"]')


def test_field_errors_render_server_side(soup):
    form = ArticleForm(data={"title": "", "slug": "x", "status": "draft"})
    assert not form.is_valid()
    html = make_schema().render(form=form)
    doc = soup(str(html))
    errors = doc.select(".dcc-field--invalid .dcc-field__errors li")
    assert any("required" in e.get_text().lower() for e in errors)


def test_unknown_field_raises_helpful_error():
    schema = Schema.make().form(ArticleForm).schema([TextInput.make("nonsense")])
    with pytest.raises(SchemaError, match="nonsense"):
        schema.render(form=ArticleForm())


def test_label_inherited_from_django_field_when_unset(soup):
    schema = Schema.make().form(ArticleForm).schema([TextInput.make("published_at")])
    doc = soup(str(schema.render(form=ArticleForm())))
    label = doc.select_one("label")
    assert "published" in label.get_text().lower()


def test_explicit_label_wins(soup):
    schema = Schema.make().form(ArticleForm).schema([TextInput.make("title").label("Headline")])
    doc = soup(str(schema.render(form=ArticleForm())))
    assert doc.select_one("label").get_text().strip().startswith("Headline")


def test_choices_come_from_model_field(soup):
    schema = Schema.make().form(ArticleForm).schema([Select.make("status")])
    doc = soup(str(schema.render(form=ArticleForm())))
    option_values = {o.get("value") for o in doc.select('select[name="status"] option')}
    assert {"draft", "live", "archived"} <= option_values


def test_model_schema_without_explicit_form(soup):
    schema = (
        Schema.make()
        .model(Article, fields=["title", "slug"])
        .schema([TextInput.make("title"), TextInput.make("slug")])
    )
    doc = soup(str(schema.render()))
    assert doc.select_one('input[name="title"]')


def test_apostrophe_value_is_escaped_not_injected(soup):
    form = ArticleForm(initial={"title": "O'Brien <script>alert(1)</script>"})
    html = str(make_schema().render(form=form))
    assert "<script>alert(1)</script>" not in html
    assert "O&#x27;Brien" in html or "O&#39;Brien" in html


def test_no_hx_attrs_on_plain_form(soup):
    html = str(make_schema().render(form=ArticleForm()))
    assert "hx-get" not in html
    assert "hx-post" not in html


def test_visible_when_compiles_to_alpine(soup):
    schema = (
        Schema.make()
        .form(ArticleForm)
        .schema(
            [Select.make("status"), TextInput.make("slug").visible_when("status", equals="live")]
        )
    )
    doc = soup(str(schema.render(form=ArticleForm())))
    wrapper = doc.select("div.dcc-field[x-show]")
    assert wrapper
    assert '"live"' in wrapper[-1].get("x-show")


def test_toggle_renders_switch(soup):
    schema = Schema.make().form(ArticleForm).schema([Toggle.make("featured")])
    doc = soup(str(schema.render(form=ArticleForm())))
    assert doc.select_one('input[type="checkbox"][role="switch"][name="featured"]')
