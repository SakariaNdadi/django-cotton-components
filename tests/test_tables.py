from __future__ import annotations

import json

import pytest
from django.http import QueryDict
from django.test import RequestFactory

from django_cotton_components.tables import (
    BadgeColumn,
    BooleanColumn,
    DateColumn,
    SelectFilter,
    Table,
    TextColumn,
)
from django_cotton_components.tables.query import apply_all
from django_cotton_components.tables.state import TableState
from tests.testapp.models import Article, Author

pytestmark = pytest.mark.django_db


@pytest.fixture
def articles():
    ada = Author.objects.create(name="Ada")
    grace = Author.objects.create(name="Grace")
    for i in range(6):
        Article.objects.create(
            title=f"Piece {i}",
            slug=f"piece-{i}",
            status="live" if i % 2 else "draft",
            featured=i == 0,
            author=ada if i < 3 else grace,
            body=f"secret-body-{i}",
        )
    return Article.objects.all()


def _table(qs) -> Table:
    return (
        Table.make(qs)
        .columns(
            [
                TextColumn.make("title").sortable().searchable(),
                TextColumn.make("author.name").label("Author").sortable(sort_field="author__name"),
                BadgeColumn.make("status"),
                BooleanColumn.make("featured"),
            ]
        )
        .filters([SelectFilter.make("status").options(Article.Status.choices)])
        .default_sort("title")
    )


def test_state_namespaces_by_table_id():
    q = QueryDict("t_foo_sort=-name&t_foo_page=3&t_bar_sort=x")
    state = TableState.from_query("foo", q)
    assert state.sort == "name"
    assert state.descending is True
    assert state.page == 3


def test_client_mode_under_threshold(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).render(RequestFactory().get("/")))
    assert 'x-data="dccTable(' in html


def test_client_mode_without_filters_is_zero_request(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    table = (
        Table.make(articles)
        .columns([TextColumn.make("title").sortable().searchable()])
        .default_sort("title")
    )
    html = str(table.render(RequestFactory().get("/")))
    assert "hx-get" not in html and "hx-post" not in html


def test_client_mode_filters_round_trip(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).render(RequestFactory().get("/")))
    # sort/pagination stay client-side; only the filter form round-trips
    assert 'hx-trigger="change"' in html
    assert "hx-get" in html.split('id="article-content"')[0]  # on the toolbar, not the rows


def test_client_mode_emits_only_declared_columns(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).render(RequestFactory().get("/")))
    # the model has a `body` field we never declared as a column
    assert "secret-body-" not in html


def test_server_mode_over_threshold(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2}
    req = RequestFactory().get("/things/")
    html = str(_table(articles).render(req))
    assert "hx-get" in html
    assert "_dcc_table=article" in html
    assert 'x-data="dccTable(' not in html


def test_forced_client_side(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 1}
    html = str(_table(articles).client_side().render(RequestFactory().get("/")))
    assert "dccTable(" in html


def test_sort_injection_ignored(articles):
    state = TableState.from_query("article", QueryDict("t_article_sort=body"))
    columns = [TextColumn.make("title").sortable()]
    qs = apply_all(articles, state, columns, [])
    # 'body' is not a sortable column -> ordering unchanged (no crash, no leak)
    assert list(qs) == list(articles)


def test_sort_injection_related_path_ignored(articles):
    state = TableState.from_query("article", QueryDict("t_article_sort=author__password"))
    qs = apply_all(articles, state, [TextColumn.make("title").sortable()], [])
    assert qs.query.order_by == ()


def test_sort_uses_column_declared_path(articles):
    state = TableState.from_query("article", QueryDict("t_article_sort=author.name"))
    col = TextColumn.make("author.name").sortable(sort_field="author__name")
    qs = apply_all(articles, state, [col], [])
    assert qs.query.order_by == ("author__name",)


def test_search_only_over_searchable_columns(articles):
    state = TableState.from_query("article", QueryDict("t_article_search=Piece 1"))
    cols = [TextColumn.make("title").searchable(), TextColumn.make("status")]
    qs = apply_all(articles, state, cols, [])
    assert qs.count() == 1


def test_filter_validates_value(articles):
    f = SelectFilter.make("status").options(Article.Status.choices)
    state = TableState(table_id="article", filters={"status": "bogus"})
    assert apply_all(articles, state, [], [f]).count() == articles.count()
    state.filters = {"status": "live"}
    assert apply_all(articles, state, [], [f]).count() == 3


def test_htmx_partial_endpoint(articles, settings, client):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2}
    # server-mode content fragment via request with the marker
    req = RequestFactory().get("/x/", {"_dcc_table": "article", "t_article_sort": "-title"})
    frag = str(_table(articles).render_content(req))
    assert "<table" in frag
    assert "Piece 5" in frag  # descending -> highest first row-ish


def test_badge_and_boolean_columns_escape(articles):
    Article.objects.create(
        title="<b>x</b>", slug="x", status="draft", author=Author.objects.first()
    )
    settings_qs = Article.objects.all()
    html = str(_table(settings_qs).client_side().render(RequestFactory().get("/")))
    assert "<b>x</b>" not in html


def test_date_column_since():
    from django.utils import timezone

    col = DateColumn.make("created_at").since()
    out = str(col.format(timezone.now()))
    assert "ago" in out


def test_client_rows_json_is_valid(articles, settings, soup):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).render(RequestFactory().get("/")))
    doc = soup(html)
    blob = doc.select_one("#article-config")
    data = json.loads(blob.string)
    assert data["perPage"]
    assert len(data["rows"]) == 6
    assert set(data["rows"][0]) == {"_pk", "0", "1", "2", "3"}
