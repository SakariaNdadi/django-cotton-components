from __future__ import annotations

import pytest
from django.test import override_settings

from django_cotton_components import htmx
from django_cotton_components.core.attributes import AttributeBag
from django_cotton_components.core.context import RenderContext
from django_cotton_components.ui import Badge, Button, Checkbox, Icon, IconButton, Menu, Modal

CTX = RenderContext()


def test_button_renders_button_by_default():
    out = str(Button.make(label="Save").variant("primary").render(CTX))
    assert out.startswith("<button")
    assert 'type="button"' in out
    assert "dcc-btn dcc-btn--primary" in out
    assert ">Save<" in out or "Save</span>" in out


def test_button_with_href_renders_anchor():
    out = str(Button.make(label="Edit").href("/a/1/").render(CTX))
    assert out.startswith("<a ") and 'href="/a/1/"' in out


def test_button_merges_htmx_bag_into_attrs():
    bag = htmx.get("/x", target="#t", swap="outerHTML")
    out = str(Button.make(label="Go").attributes(bag).render(CTX))
    assert 'hx-get="/x"' in out and 'hx-target="#t"' in out
    assert "dcc-btn" in out  # styling classes still present


def test_button_unknown_variant_warns_and_falls_back():
    with pytest.warns(UserWarning, match="Unknown button variant"):
        out = str(Button.make(label="Go").variant("prmary").render(CTX))
    assert "dcc-btn--secondary" in out


def test_button_escapes_label():
    out = str(Button.make(label="<script>").render(CTX))
    assert "<script>" not in out and "&lt;script&gt;" in out


def test_icon_button_moves_label_to_aria():
    out = str(IconButton.make(label="Toggle star").icon("star").render(CTX))
    assert 'aria-label="Toggle star"' in out
    assert "Toggle star</span>" not in out
    assert "dcc-btn--icon" in out


def test_badge_variant_class_and_escape():
    out = str(Badge.make(label="<b>").variant("danger").render(CTX))
    assert "dcc-badge dcc-badge--danger" in out
    assert "&lt;b&gt;" in out


def test_checkbox_name_value_checked():
    out = str(
        Checkbox.make("records").value("9").checked().attributes({"data-dcc-bulk": ""}).render(CTX)
    )
    assert 'name="records"' in out and 'value="9"' in out and "checked" in out
    assert "data-dcc-bulk" in out


def test_modal_teleports_and_traps():
    out = str(Modal.make().heading("Sure?").body("<p>x</p>").render(CTX))
    assert "x-trap" in out and "dcc-modal__overlay" in out
    assert "<p>x</p>" in out


def test_menu_lists_prerendered_items():
    item = Button.make(label="Delete").render(CTX)
    out = str(Menu.make().items([item]).render(CTX))
    assert "dcc-menu" in out and "Delete</span>" in out


@override_settings(DCC={"ICON_ASSET_URL": None})
def test_icon_set_can_self_host():
    from django_cotton_components.icons import icon_assets

    assert str(icon_assets()) == ""


def test_icon_unknown_token_is_empty():
    assert str(Icon.make("../evil").render(CTX)) == ""


def test_button_unknown_setter_lists_valid():
    with pytest.raises(TypeError):
        Button(label="x", nonsense=1)


def test_attribute_bag_class_merges_not_replaces():
    bag = AttributeBag({"class": "a"})
    bag.add_class("b")
    assert set(bag.as_dict()["class"].split()) == {"a", "b"}
