from __future__ import annotations

import pytest

from django_control_components.schemas import (
    EmailInput,
    Fieldset,
    FileUpload,
    Grid,
    Hidden,
    MultiSelect,
    PasswordInput,
    Radio,
    Schema,
    Section,
    Tab,
    Tabs,
    TextInput,
)
from django_control_components.schemas.fields.base import Field
from tests.testapp.forms import ArticleForm

pytestmark = pytest.mark.django_db


def render(*components) -> str:
    return str(Schema.make().form(ArticleForm).schema(list(components)).render(form=ArticleForm()))


def test_field_requires_name():
    with pytest.raises(ValueError, match="requires a field name"):
        TextInput.make()


def test_grid_renders_children(soup):
    html = render(Grid.make().columns(3).schema([TextInput.make("title"), TextInput.make("slug")]))
    doc = soup(html)
    grid = doc.select_one(".dcc-grid")
    assert "--dcc-cols: 3" in grid.get("style")
    assert doc.select_one('[name="title"]') and doc.select_one('[name="slug"]')


def test_fieldset_renders_legend(soup):
    doc = soup(render(Fieldset.make("Meta").schema([TextInput.make("slug")])))
    assert doc.select_one("fieldset legend").get_text() == "Meta"


def test_tabs_rejects_non_tab():
    with pytest.raises(TypeError, match="only Tab"):
        Tabs.make().schema([TextInput.make("title")])


def test_tabs_render(soup):
    doc = soup(
        render(
            Tabs.make().schema(
                [
                    Tab.make("One").schema([TextInput.make("title")]),
                    Tab.make("Two").schema([TextInput.make("slug")]),
                ]
            )
        )
    )
    tablist = doc.select(".dcc-tabs__tab")
    assert [t.get_text() for t in tablist] == ["One", "Two"]


def test_password_has_reveal_toggle(soup):
    # bind to a real field so the schema aligns
    schema = Schema.make().form(ArticleForm).schema([PasswordInput.make("slug")])
    doc = soup(str(schema.render(form=ArticleForm())))
    assert doc.select_one('input[type="password"]')
    assert doc.select_one("button[x-on\\:click]")


def test_radio_renders_options(soup):
    doc = soup(render(Radio.make("status")))
    values = {i.get("value") for i in doc.select('input[type="radio"][name="status"]')}
    assert {"draft", "live", "archived"} <= values


def test_multiselect_is_multiple(soup):
    doc = soup(render(MultiSelect.make("tags")))
    assert doc.select_one('select[name="tags"][multiple]')


def test_hidden_field_no_label(soup):
    schema = Schema.make().form(ArticleForm).strict().schema([Hidden.make("slug")])
    doc = soup(str(schema.render(form=ArticleForm())))
    assert doc.select_one("label") is None
    assert doc.select_one('input[type="hidden"][name="slug"]')


def test_email_input_type():
    assert EmailInput.make("slug").input_type == "email"


def test_kwargs_equal_chained_for_fields():
    a = TextInput.make("title").label("T").required().placeholder("hi")
    b = TextInput("title", label="T", required=True, placeholder="hi")
    assert a._config == b._config


def test_clone_deep_isolates_children():
    section = Section.make("A").schema([TextInput.make("title")])
    clone = section.clone()
    clone._children[0].label("changed")
    assert section._children[0]._get("label") != "changed"


def test_fileupload_spec_collects_setters():
    upload = (
        FileUpload.make("cover")
        .image()
        .max_size("2MB")
        .resize(max_width=800)
        .convert("webp")
        .strip_exif()
        .aspect_ratio("1:1")
        .min_dimensions(10, 10)
    )
    spec = upload.image_spec()
    assert spec["image"] is True
    assert spec["max_size"] == "2MB"
    assert spec["convert"] == {"format": "webp", "quality": 82}


def test_visible_when_is_in(soup):
    schema = (
        Schema.make()
        .form(ArticleForm)
        .schema([TextInput.make("slug").visible_when("status", is_in=["live", "archived"])])
    )
    doc = soup(str(schema.render(form=ArticleForm())))
    x_show = doc.select_one("div.dcc-field[x-show]").get("x-show")
    assert '["live", "archived"]' in x_show and "includes" in x_show


def test_column_span_full_emits_grid_class(soup):
    doc = soup(render(TextInput.make("title").column_span_full()))
    field = doc.select_one("div.dcc-field")
    assert "dcc-col-span-full" in field.get("class")
    assert field.get("style") is None


def test_column_span_int_emits_grid_span_style(soup):
    doc = soup(render(TextInput.make("title").column_span(2)))
    field = doc.select_one("div.dcc-field")
    assert field.get("style") == "grid-column: span 2"
    assert "dcc-col-span-full" not in (field.get("class") or [])


def test_field_without_column_span_has_no_span_markup(soup):
    doc = soup(render(TextInput.make("title")))
    field = doc.select_one("div.dcc-field")
    assert field.get("style") is None
    assert "dcc-col-span-full" not in (field.get("class") or [])


def test_layout_visible_when_now_compiles_an_expression(soup):
    schema = (
        Schema.make()
        .form(ArticleForm)
        .schema(
            [
                Section.make("Advanced")
                .visible_when("status", equals="live")
                .schema([TextInput.make("slug")])
            ]
        )
    )
    doc = soup(str(schema.render(form=ArticleForm())))
    section = doc.select_one("section.dcc-section[x-show]")
    assert section is not None
    assert '$dccField("status") == "live"' in section.get("x-show")


def test_layout_without_visible_when_has_no_x_show(soup):
    doc = soup(render(Section.make("Plain").schema([TextInput.make("title")])))
    assert doc.select_one("section.dcc-section").get("x-show") is None


def test_field_base_default_value_used_without_form():
    from django_control_components.core.context import RenderContext

    class Plain(Field):
        template_name = "django_control_components/controls/input.html"

    data = Plain("x").default("hello").get_view_data(RenderContext())
    assert data["value"] == "hello"
    assert data["label"] == "X"
