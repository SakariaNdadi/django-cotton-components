from __future__ import annotations

import pytest
from bs4 import BeautifulSoup


@pytest.fixture
def soup():
    """Parse an HTML fragment for selector-based assertions."""

    def _parse(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    return _parse


@pytest.fixture
def author(db):
    from tests.testapp.models import Author

    return Author.objects.create(name="Ada Lovelace", email="ada@example.com")


@pytest.fixture
def article(db, author):
    from tests.testapp.models import Article

    return Article.objects.create(
        title="Analytical Engine",
        slug="analytical-engine",
        body="Notes.",
        status="live",
        author=author,
    )
