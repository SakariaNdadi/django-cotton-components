from __future__ import annotations

import pytest

from django_cotton_components.panels import ChartWidget, StatWidget, TableWidget
from django_cotton_components.tables import Table, TextColumn
from tests.testapp.models import Article, Author

pytestmark = pytest.mark.django_db


def test_stat_widget_static_and_callable_value():
    assert "42" in str(StatWidget.make("N", 42).render(None))
    w = StatWidget.make("N").value(lambda: 7).description("since Tuesday").icon("star")
    out = str(w.render(None))
    assert "7" in out and "since Tuesday" in out and "fa-" in out


def test_stat_widget_value_can_take_request():
    w = StatWidget.make("N").value(lambda request: "req" if request else "no")
    assert "req" in str(w.render(object()))


def test_chart_widget_scales_bars():
    w = ChartWidget.make("By status").data([("Live", 8), ("Draft", 2)])
    out = str(w.render(None))
    assert "dcc-chart__fill" in out
    assert "width: 100.0%" in out  # the max bar
    assert "width: 25.0%" in out


def test_chart_widget_accepts_callable_data():
    w = ChartWidget.make("x").data(lambda: [("a", 1)])
    assert "dcc-chart__row" in str(w.render(None))


def test_table_widget_renders_its_table():
    Author.objects.create(name="Ada")
    Article.objects.create(title="T", slug="t", status="live", author=Author.objects.first())
    table = Table.make(Article.objects.all()).columns([TextColumn.make("title")]).client_side()
    out = str(TableWidget.make("Recent", table).render(None))
    assert "dcc-table" in out and "T" in out


def test_widget_span_override():
    assert 'style="--dcc-widget-span: 3"' in str(StatWidget.make("N", 1).columns(3).render(None))
