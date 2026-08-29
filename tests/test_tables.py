from __future__ import annotations

import json

import pytest
from django.http import QueryDict
from django.test import RequestFactory

from django_control_components.tables import (
    BadgeColumn,
    BooleanColumn,
    DateColumn,
    SelectFilter,
    Table,
    TextColumn,
)
from django_control_components.tables.query import apply_all
from django_control_components.tables.state import TableState
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


def test_stream_mode_never_counts(articles, settings):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2}
    req = RequestFactory().get("/x/", {"_dcc_table": "article"})
    with CaptureQueriesContext(connection) as cap:
        str(_table(articles).render_content(req))
    joined = " ".join(q["sql"].lower() for q in cap.captured_queries)
    assert "count(" not in joined


def test_stream_mode_appends_via_cursor(articles, settings):
    # 6 rows, per_page 2 -> first fragment has 2 rows + a "load more" sentinel
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2}
    table = _table(articles).paginate([2]).default_sort("title")
    req = RequestFactory().get("/x/", {"_dcc_table": "article"})
    frag = str(table.render_content(req))
    assert frag.count("data-dcc-row") == 2
    assert "dcc-table__more" in frag and "hx-get" in frag

    # follow the cursor
    import re

    token = re.search(r"t_article_after=([^&\"]+)", frag).group(1)
    req2 = RequestFactory().get(
        "/x/", {"_dcc_table": "article", "_dcc_rows": "1", "t_article_after": token}
    )
    rows = str(table.render_content(req2))
    assert "<table" not in rows
    assert rows.count("data-dcc-row") == 2


def test_cursor_encode_decode_roundtrip_and_bad_token():
    from django_control_components.tables import cursor

    tok = cursor.encode("2024-01-01", 7)
    assert cursor.decode(tok) == ("2024-01-01", 7)
    assert cursor.decode(None) is None
    assert cursor.decode("!!!not base64!!!") is None


def test_cursor_paginate_descending(articles):
    from django_control_components.tables import cursor

    first, token = cursor.paginate(
        articles, sort_field="title", descending=True, after=None, per_page=2
    )
    assert [a.title for a in first] == ["Piece 5", "Piece 4"]
    assert token is not None
    nxt, _ = cursor.paginate(articles, sort_field="title", descending=True, after=token, per_page=2)
    assert [a.title for a in nxt] == ["Piece 3", "Piece 2"]


def test_page_numbers_strategy_still_counts(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2}
    req = RequestFactory().get("/x/", {"_dcc_table": "article"})
    frag = str(_table(articles).page_numbers().render_content(req))
    assert "Page 1 of" in frag


def test_client_rows_json_is_valid(articles, settings, soup):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).render(RequestFactory().get("/")))
    doc = soup(html)
    blob = doc.select_one("#article-config")
    data = json.loads(blob.string)
    assert data["perPage"]
    assert len(data["rows"]) == 6
    assert set(data["rows"][0]) == {"_pk", "0", "1", "2", "3"}


def test_grid_height_follows_row_count(articles, settings):
    """A short result set collapses the grid; no filler rows, no min-height."""
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2, "TABLE_PER_PAGE_CHOICES": [10]}
    req = RequestFactory().get("/x/", {"_dcc_table": "article"})
    frag = str(_table(articles).page_numbers().render_content(req))
    assert "dcc-table__row--filler" not in frag
    assert "--dcc-table-min-rows" not in frag
    assert frag.count("data-dcc-row") == 6  # exactly the rows that exist


def test_pagination_position_class(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2, "TABLE_PER_PAGE_CHOICES": [10]}
    req = RequestFactory().get("/x/", {"_dcc_table": "article"})
    frag = str(_table(articles).page_numbers().pagination_position("center").render_content(req))
    assert "dcc-table__pagination--center" in frag


def test_feed_presentation_renders_list_not_grid(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).presentation("feed").render(RequestFactory().get("/")))
    assert 'class="dcc-feed"' in html
    assert "dcc-table__grid" not in html


def test_infinite_scroll_client_has_sentinel_no_pager(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).infinite_scroll().render(RequestFactory().get("/")))
    assert "data-dcc-sentinel" in html
    assert "dcc-table__pagination" not in html


def test_infinite_scroll_server_uses_cursor_strategy(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2, "TABLE_PER_PAGE_CHOICES": [2]}
    req = RequestFactory().get("/x/", {"_dcc_table": "article"})
    frag = str(_table(articles).infinite_scroll().render_content(req))
    assert "Page 1 of" not in frag  # no COUNT / numbered pager
    assert 'hx-trigger="revealed"' in frag  # append-on-scroll load-more


def test_bulk_toolbar_lives_inside_content(articles, settings):
    from django_control_components.actions import BulkAction

    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    table = _table(articles).bulk_actions([BulkAction.make("archive").action(lambda records: None)])
    html = str(table.render(RequestFactory().get("/")))
    content_at = html.index('id="article-content"')
    assert html.index("dcc-table__bulk") > content_at


def test_per_page_selector_client(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).paginate([10, 25, 50]).render(RequestFactory().get("/")))
    assert 'x-model.number="perPage"' in html
    assert html.count("<option") >= 3


def test_per_page_selector_server_round_trips(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 2}
    req = RequestFactory().get("/x/", {"_dcc_table": "article"})
    frag = str(_table(articles).paginate([10, 25, 50]).page_numbers().render_content(req))
    assert 'name="t_article_per_page"' in frag
    assert 'hx-trigger="change"' in frag


def test_single_per_page_choice_hides_selector(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(_table(articles).paginate([25]).render(RequestFactory().get("/")))
    assert "dcc-table__perpage" not in html


def test_infinite_scroll_hides_per_page_selector(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(
        _table(articles).paginate([10, 25]).infinite_scroll().render(RequestFactory().get("/"))
    )
    assert "dcc-table__perpage" not in html


def test_no_paginate_call_hides_per_page_selector(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}  # default choices [10,25,50,100]
    html = str(_table(articles).render(RequestFactory().get("/")))
    assert "dcc-table__perpage" not in html


def test_record_url_makes_rows_clickable(articles, settings):
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(
        _table(articles)
        .record_url(lambda record: f"/things/{record.pk}/")
        .render(RequestFactory().get("/"))
    )
    assert 'data-dcc-href="/things/' in html
    assert html.count("dcc-table__row--clickable") == articles.count()
    assert 'role="link"' in html


def test_record_preview_renders_hover_template(articles, settings):
    from django.utils.html import format_html

    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    html = str(
        _table(articles)
        .record_preview(lambda record: format_html("<b>{}</b>", record.title))
        .render(RequestFactory().get("/"))
    )
    assert '<template class="dcc-row-preview"><b>Piece 0</b></template>' in html


def test_record_action_registers_and_marks_rows(articles, settings):
    from django_control_components.actions import Action, registry

    registry.clear()
    settings.DCC = {"TABLE_CLIENT_SIDE_MAX_ROWS": 100}
    view = Action.make("peek").modal(lambda record: "<p>hi</p>")
    table = _table(articles).id("things").record_action(view)
    html = str(table.render(RequestFactory().get("/")))
    assert "data-dcc-action=" in html
    assert 'id="dcc-modal-table-things"' in html  # modal mount rendered
    assert registry.resolve("table-things", "peek") is not None
    registry.clear()
