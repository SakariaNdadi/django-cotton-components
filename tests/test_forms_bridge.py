from __future__ import annotations

import pytest

from django_cotton_components.schemas import MultiSelect, Schema, Section, Select, TextInput
from tests.testapp.forms import ArticleForm
from tests.testapp.models import Author, Tag

pytestmark = pytest.mark.django_db


@pytest.fixture
def refs():
    author = Author.objects.create(name="Ada")
    tags = [Tag.objects.create(name=n) for n in ("a", "b")]
    return author, tags


def full_schema() -> Schema:
    return (
        Schema.make()
        .form(ArticleForm)
        .schema(
            [
                Section.make("Main").schema(
                    [
                        TextInput.make("title"),
                        TextInput.make("slug"),
                        TextInput.make("body"),
                        Select.make("status"),
                        Select.make("author"),
                        MultiSelect.make("tags"),
                    ]
                )
            ]
        )
    )


def test_no_js_post_still_validates(refs):
    author, tags = refs
    schema = full_schema()
    data = {
        "title": "Hello",
        "slug": "hello",
        "body": "x",
        "status": "draft",
        "author": str(author.pk),
        "tags": [str(tags[0].pk)],
    }
    form = schema.build_form(data=data)
    assert form.is_valid(), form.errors
    article = form.save()
    assert article.author == author
    assert list(article.tags.all()) == [tags[0]]


def test_cleaned_data_and_custom_clean_run(refs):
    author, _ = refs
    schema = full_schema()
    form = schema.build_form(
        data={"title": "T", "slug": "reserved", "status": "draft", "author": str(author.pk)}
    )
    assert not form.is_valid()
    assert "slug" in form.errors


def test_initial_from_instance_renders_selected(soup, refs):
    author, tags = refs
    from tests.testapp.models import Article

    article = Article.objects.create(
        title="Existing", slug="existing", status="live", author=author
    )
    article.tags.set(tags)
    html = str(full_schema().render(form=ArticleForm(instance=article)))
    doc = soup(html)
    selected = {o.get("value") for o in doc.select('select[name="status"] option[selected]')}
    assert "live" in selected


def test_unmapped_fields_appended(soup):
    schema = Schema.make().form(ArticleForm).schema([TextInput.make("title")])
    doc = soup(str(schema.render(form=ArticleForm())))
    # featured/published_at etc. were not declared but still render
    assert doc.select_one('[name="published_at"]')


def test_strict_mode_omits_unmapped(soup):
    schema = Schema.make().form(ArticleForm).strict().schema([TextInput.make("title")])
    doc = soup(str(schema.render(form=ArticleForm())))
    assert doc.select_one('[name="title"]')
    assert doc.select_one('[name="published_at"]') is None
