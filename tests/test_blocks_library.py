"""The concrete layout + chrome blocks (blocks/layout.py, blocks/chrome.py)."""

from __future__ import annotations

import pytest

from django_control_components.blocks import (
    BLOCK_TYPES,
    AppShell,
    Card,
    Column,
    Divider,
    Footer,
    Grid,
    Navbar,
    Row,
    Sidebar,
    Spacer,
    Stack,
)
from django_control_components.core.context import RenderContext

pytestmark = pytest.mark.django_db


def r(block) -> str:
    return str(block.render(RenderContext(request=None)))


class _Leaf(Divider):
    template_name = "test_blocks/leaf.html"


def test_stack_maps_gap_keyword_to_a_length():
    html = r(Stack.make().gap("lg").fill("default", [_Leaf.make()]))
    assert "flex-direction:column" in html
    assert "gap:1.5rem" in html
    assert "<leaf/>" in html


def test_row_translates_justify_between():
    html = r(Row.make().justify("between").wrap(False).fill("default", []))
    assert "justify-content:space-between" in html
    assert "flex-wrap:nowrap" in html


def test_grid_defaults_to_twelve_tracks():
    assert "--dcc-cols:12" in r(Grid.make().fill("default", []))
    assert "--dcc-cols:4" in r(Grid.make().cols(4).fill("default", []))


def test_column_span_and_offset():
    assert "grid-column:span 3" in r(Column.make().span(3).fill("default", []))
    assert "grid-column:2 / span 3" in r(Column.make().span(3).offset(1).fill("default", []))


def test_card_renders_header_only_when_present():
    plain = r(Card.make().fill("body", [_Leaf.make()]))
    assert "dcc-card__header" not in plain
    titled = r(Card.make().title("Stats").fill("body", [_Leaf.make()]))
    assert "dcc-card__header" in titled and "Stats" in titled


def test_card_footer_slot_is_optional():
    assert "dcc-card__footer" not in r(Card.make().fill("body", []))
    assert "dcc-card__footer" in r(Card.make().fill("footer", [_Leaf.make()]))


def test_divider_and_spacer_are_leaves():
    assert r(Divider.make()).strip() == '<hr class="dcc-divider">'
    assert "height:1.5rem" in r(Spacer.make())
    assert "height:0.5rem" in r(Spacer.make().size("sm"))


def test_app_shell_omits_sidebar_chrome_when_slot_empty():
    bare = r(AppShell.make().fill("content", [_Leaf.make()]))
    assert "dcc-panel__navtoggle" not in bare
    assert "dcc-panel__main" in bare

    full = r(
        AppShell.make()
        .fill("sidebar", [Sidebar.make().brand("Admin")])
        .fill("content", [_Leaf.make()])
    )
    assert "dcc-panel__navtoggle" in full
    assert "dcc-panel__nav" in full and "Admin" in full


def test_navbar_regions():
    html = r(Navbar.make().brand("Shop").fill("end", [_Leaf.make()]))
    assert "dcc-navbar__brand" in html and "Shop" in html
    assert "dcc-navbar__end" in html


def test_footer_wraps_children():
    assert (
        r(Footer.make().fill("default", [_Leaf.make()])).strip()
        == '<footer class="dcc-footer"><leaf/></footer>'
    )


# -- registry -------------------------------------------------------


def test_every_block_is_registered_and_describable():
    expected = {
        "Stack",
        "Row",
        "Grid",
        "Column",
        "Card",
        "Divider",
        "Spacer",
        "AppShell",
        "Navbar",
        "Sidebar",
        "Footer",
    }
    assert expected <= set(BLOCK_TYPES.names())
    for name in expected:
        info = BLOCK_TYPES.info(name)
        assert info.category == "block"


def test_blocks_appear_in_the_studio_palette():
    from django_control_components.studio.palette import palette

    pal = palette(None)
    assert "blocks" in pal
    names = {entry["name"] for entry in pal["blocks"]}
    assert {"AppShell", "Grid", "Card"} <= names
