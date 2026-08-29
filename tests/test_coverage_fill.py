from __future__ import annotations

import io

import pytest
from django.test import RequestFactory
from django.utils import timezone

from django_control_components.core.context import RenderContext
from django_control_components.schemas import Schema, TextInput
from django_control_components.schemas.endpoints import (
    SchemaValidateView,
    clear_schemas,
    register_schema,
)
from django_control_components.tables.columns import (
    BadgeColumn,
    BooleanColumn,
    DateColumn,
    ImageColumn,
    TextColumn,
)
from django_control_components.tables.filters import (
    BooleanFilter,
    Filter,
    SelectFilter,
    TernaryFilter,
)
from tests.testapp.forms import ArticleForm
from tests.testapp.models import Article, Author

pytestmark = pytest.mark.django_db


# ---- columns -------------------------------------------------------------


def test_column_kwargs_and_unknown_setter():
    col = TextColumn.make("title", label="T", sortable=True, limit=5)
    assert col.header == "T"
    assert col.is_sortable
    with pytest.raises(TypeError, match="no setter"):
        TextColumn.make("x", bogus=1)


def test_text_column_limit_and_dotted_path():
    author = Author.objects.create(name="Very Long Name Indeed")
    art = Article.objects.create(title="t", slug="s", status="draft", author=author)
    col = TextColumn.make("author.name").limit(6)
    ctx = RenderContext()
    assert str(col.render_cell(art, ctx)).endswith("…")


def test_state_fn_column():
    art = Article(title="hi")
    col = TextColumn.make("x").state(lambda record: record.title.upper())
    assert str(col.render_cell(art, RenderContext())) == "HI"


def test_boolean_badge_date_columns():
    assert "Yes" in str(BooleanColumn.make("f").format(True))
    assert "No" in str(BooleanColumn.make("f").labels(("On", "Off")).format(False)) or "Off" in str(
        BooleanColumn.make("f").labels(("On", "Off")).format(False)
    )
    assert str(BadgeColumn.make("s").format(None)) == ""
    assert "draft" in str(BadgeColumn.make("s").colors({"draft": "gray"}).format("draft"))
    d = DateColumn.make("d")
    assert str(d.format(None)) == ""
    assert "ago" in str(DateColumn.make("d").since().format(timezone.now()))
    assert str(DateColumn.make("d").date_format("Y").format(timezone.now()))


def test_image_column(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    from django.core.files.base import ContentFile
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (20, 20)).save(buf, format="PNG")
    author = Author.objects.create(name="a")
    author.avatar.save("a.png", ContentFile(buf.getvalue()), save=True)

    col = ImageColumn.make("avatar").thumbnail((16, 16)).rounded()
    html = str(col.render_cell(author, RenderContext()))
    assert "<img" in html and "dcc-image-thumb--round" in html
    assert col.cell_text(author, RenderContext())  # returns a url string
    assert str(ImageColumn.make("avatar").format(None)) == ""


# ---- filters ------------------------------------------------------------


def test_filter_base_and_unknown_setter():
    with pytest.raises(TypeError):
        Filter("x", bogus=1)
    f = Filter("status", label="Status")
    assert f.header == "Status"
    qs = Article.objects.all()
    assert f.apply(qs, None) is qs


def test_select_filter_rejects_out_of_range():
    f = SelectFilter.make("status").options(Article.Status.choices)
    assert f.clean("bogus") is None
    assert f.clean("live") == "live"
    assert ("", "All") in f.choices()


def test_boolean_and_ternary_filter():
    f = BooleanFilter.make("featured")
    assert f.clean("true") is True
    assert f.clean("false") is False
    assert f.clean("maybe") is None
    assert dict(f.choices())[""] == "All"
    assert isinstance(TernaryFilter.make("f"), BooleanFilter)


# ---- live validation endpoint ---------------------------------------


@pytest.fixture(autouse=True)
def _clear():
    clear_schemas()
    yield
    clear_schemas()


def test_schema_validate_view_returns_field_fragment():
    schema = Schema.make().form(ArticleForm).strict().schema([TextInput.make("title")])
    register_schema("art", schema)
    req = RequestFactory().post("/dcc/v/art/", {"_field": "title", "title": ""})
    resp = SchemaValidateView.as_view()(req, schema_key="art")
    assert resp.status_code == 200
    assert b"dcc-field" in resp.content


def test_schema_validate_unknown_schema_and_field():
    from django.http import Http404

    req = RequestFactory().post("/x/", {"_field": "title"})
    with pytest.raises(Http404):
        SchemaValidateView.as_view()(req, schema_key="nope")

    schema = Schema.make().form(ArticleForm).strict().schema([TextInput.make("title")])
    register_schema("art", schema)
    req2 = RequestFactory().post("/x/", {})
    assert SchemaValidateView.as_view()(req2, schema_key="art").status_code == 400
    req3 = RequestFactory().post("/x/", {"_field": "ghost"})
    with pytest.raises(Http404):
        SchemaValidateView.as_view()(req3, schema_key="art")


# ---- action setters + run() injection ------------------------------


def test_action_setters_and_run_injection():
    from django_control_components.actions import Action, BulkAction

    seen = {}

    def cb(record, request, user, data):
        seen.update(r=record, req=request, u=user, d=data)

    a = (
        Action.make("x")
        .icon("i")
        .color("danger")
        .variant("danger")
        .modal_description("d")
        .success_notification("ok")
        .action(cb)
    )
    a.bind_owner("owner")
    a.run(RequestFactory().get("/"), [Article(title="t")], {"k": 1})
    assert seen["d"] == {"k": 1}
    assert a.success_message() == "ok"

    b = BulkAction.make("y").action(lambda records: seen.update(n=len(records)))
    b.run(RequestFactory().get("/"), [1, 2, 3], {})
    assert seen["n"] == 3

    assert Action.make("z").run(RequestFactory().get("/"), [], {}) is None  # no callback


def test_pipeline_resize_and_convert(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    from django.core.files.base import ContentFile
    from PIL import Image

    from django_control_components.images.pipeline import process_image
    from django_control_components.images.specs import ImageSpec

    buf = io.BytesIO()
    Image.new("RGB", (400, 300), (1, 2, 3)).save(buf, format="PNG")
    author = Author.objects.create(name="a")
    author.avatar.save("a.png", ContentFile(buf.getvalue()), save=True)

    process_image(
        author.avatar,
        ImageSpec(resize={"max_width": 100}, convert={"format": "jpeg", "quality": 70}),
    )
    author.avatar.open()
    out = Image.open(author.avatar)
    assert out.width <= 100
    assert out.format == "JPEG"
