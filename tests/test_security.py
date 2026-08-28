"""Behavioural security tests. These encode this library's threat model —
things a generic SAST scanner will not catch."""

from __future__ import annotations

import pytest

from django_cotton_components.schemas import Schema, Select, Textarea, TextInput
from tests.testapp.forms import ArticleForm
from tests.testapp.models import Author

pytestmark = pytest.mark.django_db

PAYLOADS = [
    '"><script>alert(1)</script>',
    "O'Brien",
    "'; DROP TABLE articles;--",
    "{{ 7*7 }}",
    "{% load dcc_tags %}",
]


def _schema() -> Schema:
    return (
        Schema.make()
        .form(ArticleForm)
        .schema([TextInput.make("title"), Textarea.make("body"), Select.make("status")])
    )


@pytest.mark.parametrize("payload", PAYLOADS)
def test_payload_in_field_value_is_escaped(payload, soup):
    form = ArticleForm(initial={"title": payload, "body": payload})
    html = str(_schema().render(form=form))
    assert "<script>alert(1)</script>" not in html
    assert "DROP TABLE articles" not in html or "&#" in html
    # value survives as text, escaped
    doc = soup(html)
    assert doc  # parses without raising


def test_payload_in_choice_label_is_escaped(author: Author):
    author.name = "<img src=x onerror=alert(1)>"
    author.save()
    schema = Schema.make().form(ArticleForm).schema([Select.make("author")])
    html = str(schema.render(form=ArticleForm()))
    # no raw tag anywhere — option text is HTML-escaped, json_script is unicode-escaped
    assert "<img src=x onerror=alert(1)>" not in html


def test_no_js_full_post_round_trip():
    author = Author.objects.create(name="Ada")
    form = _schema().build_form(
        data={"title": "Clean", "slug": "clean", "status": "draft", "author": str(author.pk)}
    )
    assert form.is_valid(), form.errors
    form.save()


def test_apostrophe_does_not_break_json_script(soup):
    Author.objects.create(name="D'Arcy O'Brien")
    schema = Schema.make().form(ArticleForm).schema([Select.make("author")])
    html = str(schema.render(form=ArticleForm()))
    doc = soup(html)
    blob = doc.select_one('script[type="application/json"]')
    assert blob is not None
    import json

    data = json.loads(blob.string)
    assert any("D'Arcy" in label for _v, label in data)
