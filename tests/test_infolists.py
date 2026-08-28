from __future__ import annotations

import pytest

from django_cotton_components.infolists import (
    BadgeEntry,
    BooleanEntry,
    DateEntry,
    Infolist,
    TextEntry,
)
from tests.testapp.models import Article, Author

pytestmark = pytest.mark.django_db


@pytest.fixture
def article():
    ada = Author.objects.create(name="Ada")
    return Article.objects.create(
        title="Hello", slug="hello", status="live", featured=True, author=ada
    )


def test_default_infolist_lists_every_field(article):
    html = str(Infolist.make().model(Article).render(record=article))
    assert "dcc-infolist" in html
    assert "Hello" in html and "Title" in html


def test_declared_entries_only(article):
    html = str(
        Infolist.make()
        .schema([TextEntry.make("title"), TextEntry.make("author.name").label("Author")])
        .render(record=article)
    )
    assert "Hello" in html and "Ada" in html
    assert "Slug" not in html


def test_entry_escapes_value(article):
    article.title = "<script>"
    html = str(Infolist.make().schema([TextEntry.make("title")]).render(record=article))
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_badge_and_boolean_and_date_entries(article):
    html = str(
        Infolist.make()
        .schema(
            [
                BadgeEntry.make("status").colors({"live": "success"}),
                BooleanEntry.make("featured"),
                DateEntry.make("created_at").since(),
            ]
        )
        .render(record=article)
    )
    assert "dcc-badge--success" in html
    assert "Yes" in html
    assert "ago" in html


def test_placeholder_for_empty(article):
    article.body = ""
    html = str(
        Infolist.make()
        .schema([TextEntry.make("body").placeholder("(none)")])
        .render(record=article)
    )
    assert "(none)" in html
