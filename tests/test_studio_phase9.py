"""Phase 9: the escape hatches — @block decorator, extended ALIASABLE_KEYS,
and `dcc_scaffold --eject` (spec -> Python)."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from django_control_components.blocks import BLOCK_TYPES, Block, block
from django_control_components.studio.callables import ALIASABLE_KEYS
from django_control_components.studio.scaffold import eject_to_python, scaffold_spec

pytestmark = pytest.mark.django_db


def test_block_decorator_registers_a_custom_block():
    @block("Callout", icon="bullhorn")
    class Callout(Block):
        slots = ("default",)
        template_name = "x/callout.html"

    assert BLOCK_TYPES.get("Callout") is Callout
    assert BLOCK_TYPES.info("Callout").label == "Callout"
    assert BLOCK_TYPES.info("Callout").accepts_children is True


def test_aliasable_keys_grew_but_never_includes_authorize():
    assert {"label", "url"} <= ALIASABLE_KEYS
    assert "authorize" not in ALIASABLE_KEYS


def test_an_alias_on_label_resolves_through_a_spec(settings):
    from django_control_components.studio.deserialize import _instantiate
    from django_control_components.tables import COLUMN_TYPES

    settings.DCC = {"STUDIO_CALLABLES": {"stamp": "tests.test_studio_phase9.stamp"}}
    column = _instantiate(
        COLUMN_TYPES,
        {"type": "TextColumn", "name": "title", "config": {"label": "@stamp"}},
        "col",
    )
    assert column._config["label"] is stamp


def stamp(*args, **kwargs):  # target for the alias above
    return "stamped"


# -- eject ------------------------------------------------------


def _article_spec():
    from tests.testapp.models import Article

    return "testapp.Article", scaffold_spec(Article)


def test_eject_emits_compilable_python_with_the_columns():
    label, spec = _article_spec()
    source = eject_to_python(label, spec)
    compile(source, "<ejected>", "exec")
    assert "class ArticleResource(Resource):" in source
    assert 'apps.get_model("testapp", "Article")' in source
    assert "Table.make(cls.get_queryset(request))" in source
    # a scaffolded column name shows up in the generated .columns([...])
    assert 'TextColumn.make("title")' in source or '.make("title")' in source


def test_dcc_scaffold_eject_command_prints_the_source():
    out = StringIO()
    call_command("dcc_scaffold", "testapp.Article", "--eject", stdout=out)
    assert "class ArticleResource(Resource):" in out.getvalue()
