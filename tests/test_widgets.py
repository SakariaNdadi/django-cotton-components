from __future__ import annotations

import json

import pytest

from django_control_components.panels import (
    BarListWidget,
    ChartWidget,
    StatWidget,
    TableWidget,
)
from django_control_components.tables import Table, TextColumn
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


def test_bar_list_widget_scales_bars():
    w = BarListWidget.make("By status").data([("Live", 8), ("Draft", 2)])
    out = str(w.render(None))
    assert "dcc-chart__fill" in out
    assert "width: 100.0%" in out  # the max bar
    assert "width: 25.0%" in out


def test_bar_list_widget_accepts_callable_data():
    w = BarListWidget.make("x").data(lambda: [("a", 1)])
    assert "dcc-chart__row" in str(w.render(None))


def test_chart_widget_renders_canvas_and_payload():
    w = ChartWidget.make("By status").kind("line").data([("Live", 8), ("Draft", 2)])
    out = str(w.render(None))
    assert "dccChart(" in out
    assert "<canvas" in out
    assert "chart.js" in str(w.get_assets()[0].url)
    blob = out.split('type="application/json">', 1)[1].split("</script>", 1)[0]
    payload = json.loads(blob)
    assert payload["library"] == "chartjs"
    assert payload["type"] == "line"
    assert payload["data"]["labels"] == ["Live", "Draft"]
    assert payload["data"]["datasets"][0]["data"] == [8, 2]


def test_chart_widget_area_is_a_filled_line():
    w = ChartWidget.make("x").kind("area").data([("a", 1)])
    payload = json.loads(
        str(w.render(None)).split('type="application/json">', 1)[1].split("</script>", 1)[0]
    )
    assert payload["type"] == "line"
    assert payload["data"]["datasets"][0]["fill"] is True


def test_chart_widget_rejects_unknown_kind():
    with pytest.raises(ValueError):
        ChartWidget.make("x").kind("sankey")


def test_widget_shell_wraps_content_with_stable_id():
    w = ChartWidget.make("x").id("sales")
    out = str(w.render(None))
    assert 'id="sales"' in out
    assert 'id="sales-content"' in out


def test_auto_refresh_widget_emits_poll_trigger():
    from django.test import RequestFactory

    request = RequestFactory().get("/dash/")
    out = str(StatWidget.make("N", 1).poll(15).render(request))
    assert "_dcc_widget=" in out
    assert "every 15s" in out


def test_table_widget_renders_its_table():
    Author.objects.create(name="Ada")
    Article.objects.create(title="T", slug="t", status="live", author=Author.objects.first())
    table = Table.make(Article.objects.all()).columns([TextColumn.make("title")]).client_side()
    out = str(TableWidget.make("Recent", table).render(None))
    assert "dcc-table" in out and "T" in out


def test_widget_span_override():
    assert 'style="--dcc-widget-span: 3"' in str(StatWidget.make("N", 1).columns(3).render(None))
