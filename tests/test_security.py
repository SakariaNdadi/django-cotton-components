"""Behavioural security tests. These encode this library's threat model —
things a generic SAST scanner will not catch."""

from __future__ import annotations

import pytest

from django_control_components.schemas import Schema, Select, Textarea, TextInput
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


def test_traverse_refuses_alters_data_callables():
    from django_control_components.core.paths import traverse

    class Rec:
        calls: list[int] = []

        def delete(self):
            Rec.calls.append(1)
            return "gone"

        delete.alters_data = True  # type: ignore[attr-defined]

    assert traverse(Rec(), "delete") is None
    assert Rec.calls == []


def test_traverse_refuses_private_segments():
    from django_control_components.core.paths import traverse

    class Rec:
        _secret = "leaked"

    assert traverse(Rec(), "_secret") is None
    assert traverse(Rec(), "__class__") is None


def test_spec_column_named_delete_renders_empty_and_keeps_the_row(article):
    from django_control_components.studio.deserialize import build_table_from_spec
    from tests.testapp.models import Article

    spec = {"columns": [{"type": "TextColumn", "name": "delete"}]}
    table = build_table_from_spec(Article.objects.all(), spec)
    html = str(table.render(None))
    assert "gone" not in html
    assert Article.objects.filter(pk=article.pk).exists()


def test_validate_spec_rejects_privileged_setter_from_non_superuser():
    """`allow_html` is `requires="superuser"`. The palette hides it, but a
    hand-crafted POST must be rejected server-side too — otherwise a `use_studio`
    holder can plant stored XSS in a column."""
    from types import SimpleNamespace

    from django.core.exceptions import ValidationError

    from django_control_components.studio.deserialize import validate_spec
    from tests.testapp.models import Article

    hostile = {
        "table": {
            "columns": [{"type": "TextColumn", "name": "title", "config": {"allow_html": True}}]
        }
    }

    non_super = SimpleNamespace(user=SimpleNamespace(is_superuser=False, is_authenticated=True))
    with pytest.raises(ValidationError, match="superuser"):
        validate_spec(hostile, model=Article, request=non_super)

    # a superuser may; a server-side (request-less) build is trusted
    superu = SimpleNamespace(user=SimpleNamespace(is_superuser=True, is_authenticated=True))
    validate_spec(hostile, model=Article, request=superu)
    validate_spec(hostile, model=Article)


def test_validate_spec_rejects_oversized_and_over_deep_specs():
    import pytest as _pytest
    from django.core.exceptions import ValidationError

    from django_control_components.studio.deserialize import validate_spec

    huge = {"table": {"columns": [{"type": "TextColumn", "name": "x" * 2000}] * 40}}
    with _pytest.raises(ValidationError):
        validate_spec(huge)

    deep: dict = {"table": {}}
    node = deep["table"]
    for _ in range(12):
        node["child"] = {}
        node = node["child"]
    with _pytest.raises(ValidationError):
        validate_spec(deep)


def test_permission_prefix_keeps_actions_distinct():
    from django_control_components.panels.resource import Resource
    from tests.testapp.models import Article

    class R(Resource):
        model = Article
        permission_prefix = "blog.article"

    assert R.perm("view") == "blog.view_article"
    assert R.perm("delete") == "blog.delete_article"
    assert R.perm("add") == "blog.add_article"

    class R2(Resource):
        model = Article
        permission_prefix = "widget"

    assert R2.perm("view") == "testapp.view_widget"


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
