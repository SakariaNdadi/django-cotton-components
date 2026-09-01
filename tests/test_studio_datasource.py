"""Phase 6: the DataSource prop (widget .query DSL generalised) and the
now-registered TableWidget."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from django_control_components.panels import WIDGET_TYPES, TableWidget
from django_control_components.studio.datasource import (
    resolve_queryset,
    resolve_table,
    validate_data_source,
)
from django_control_components.studio.deserialize import (
    build_widgets_from_spec,
    validate_widgets_spec,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def studio_models(settings):
    settings.DCC = {"STUDIO_MODELS": ["testapp.Article"]}


@pytest.fixture
def articles(db):
    from tests.testapp.models import Article, Author

    author = Author.objects.create(name="Ada")
    for i in range(3):
        Article.objects.create(title=f"A{i}", slug=f"a{i}", status="live", author=author)
    return author


def test_table_widget_is_registered():
    assert "TableWidget" in WIDGET_TYPES.names()
    assert WIDGET_TYPES.get("TableWidget") is TableWidget


def test_validate_rejects_a_model_outside_studio_models(settings):
    settings.DCC = {"STUDIO_MODELS": []}
    with pytest.raises(ValidationError, match="STUDIO_MODELS"):
        validate_data_source({"model": "testapp.Article"})


def test_validate_rejects_a_field_outside_safe_paths(studio_models):
    with pytest.raises(ValidationError, match="not an allowed path"):
        validate_data_source({"model": "testapp.Article", "fields": ["author__email__nope"]})


def test_validate_allows_a_relation_one_deep_and_a_lookup_on_a_filter(studio_models):
    validate_data_source(
        {
            "model": "testapp.Article",
            "fields": ["title", "author__name"],
            "filter": {"status__in": ["live"]},
            "order_by": ["-created_at"],
        }
    )


def test_resolve_queryset_applies_filter_order_and_limit(studio_models, articles):
    rows = resolve_queryset(
        {
            "model": "testapp.Article",
            "filter": {"status": "live"},
            "order_by": ["-title"],
            "limit": 2,
        }
    )
    rows = list(rows)
    assert len(rows) == 2
    assert rows[0].title == "A2"


def test_resolve_table_builds_a_column_per_field(studio_models, articles):
    table = resolve_table({"model": "testapp.Article", "fields": ["title", "status"]})
    html = str(table.render(None))
    assert "A0" in html and "live" in html


def test_widgets_spec_validates_an_embedded_data_source(studio_models):
    node = {
        "type": "TableWidget",
        "config": {"data_source": {"model": "testapp.Article", "fields": ["title"]}},
    }
    validate_widgets_spec([node])
    bad = {
        "type": "TableWidget",
        "config": {"data_source": {"model": "testapp.Article", "fields": ["secret__field"]}},
    }
    with pytest.raises(ValidationError):
        validate_widgets_spec([bad])


def test_build_widgets_wires_a_data_source_into_a_live_table(studio_models, articles):
    node = {
        "type": "TableWidget",
        "name": "Recent",
        "config": {"data_source": {"model": "testapp.Article", "fields": ["title"]}},
    }
    widget = build_widgets_from_spec([node])[0]
    assert isinstance(widget, TableWidget)
    html = str(widget.render(None))
    assert "A0" in html
