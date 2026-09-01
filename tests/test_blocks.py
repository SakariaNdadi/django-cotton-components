"""blocks/base.py (multi-slot Block) and blocks/codec.py (wire<->stored)."""

from __future__ import annotations

import pytest

from django_control_components.blocks import BLOCK_TYPES, Block
from django_control_components.blocks.codec import decode_node, decode_nodes, encode_nodes
from django_control_components.core.context import RenderContext


class _Leaf(Block):
    template_name = "test_blocks/leaf.html"


class _Shell(Block):
    slots = ("topbar", "content")
    template_name = "test_blocks/shell.html"


def test_block_has_no_slots_by_default():
    leaf = _Leaf.make("a")
    assert leaf.slot_children("anything") == []
    with pytest.raises(ValueError, match="no slot"):
        leaf.fill("content", [])


def test_fill_rejects_non_block_children():
    shell = _Shell.make()
    with pytest.raises(TypeError, match="only Block instances"):
        shell.fill("content", [object()])  # type: ignore[list-item]


def test_fill_and_slot_children_round_trip():
    shell = _Shell.make()
    a, b = _Leaf.make("a"), _Leaf.make("b")
    shell.fill("content", [a, b])
    assert shell.slot_children("content") == [a, b]
    assert shell.slot_children("topbar") == []


def test_render_slot_renders_children_in_order():
    # templates live under tests/testapp/templates/test_blocks/ (APP_DIRS)
    shell = _Shell.make().fill("content", [_Leaf.make(), _Leaf.make()])
    html = str(shell.render(RenderContext(request=None)))
    assert html == "<leaf/><leaf/>"


def test_block_types_registry_register_and_describe():
    BLOCK_TYPES.register(_Shell, name="TestShellOnce", label="Test Shell")
    assert "TestShellOnce" in BLOCK_TYPES.names()
    info = BLOCK_TYPES.info("TestShellOnce")
    assert info.label == "Test Shell"
    assert BLOCK_TYPES.get("TestShellOnce") is _Shell


# -- codec ------------------------------------------------------------


def test_encode_folds_name_into_config():
    stored = [{"type": "TextColumn", "name": "title", "config": {"sortable": True}}]
    wire = encode_nodes(stored)
    assert wire == [
        {"id": "n0", "type": "TextColumn", "config": {"sortable": True, "name": "title"}}
    ]


def test_encode_prefixes_id():
    stored = [{"type": "StatWidget", "name": "Total"}]
    assert encode_nodes(stored, id_prefix="w")[0]["id"] == "w0"


def test_encode_skips_non_dict_entries():
    assert encode_nodes([{"type": "X"}, "garbage", None]) == [
        {"id": "n0", "type": "X", "config": {}}
    ]


def test_encode_handles_none_and_empty():
    assert encode_nodes(None) == []
    assert encode_nodes([]) == []


def test_decode_lifts_name_out_of_config():
    wire = {"type": "TextColumn", "config": {"sortable": True, "name": "title"}}
    assert decode_node(wire) == {
        "type": "TextColumn",
        "name": "title",
        "config": {"sortable": True},
    }


def test_decode_omits_empty_config_and_missing_name():
    assert decode_node({"type": "TextColumn", "config": {}}) == {"type": "TextColumn"}
    assert decode_node({"type": "TextColumn"}) == {"type": "TextColumn"}


def test_decode_nodes_skips_non_dict_and_defaults_missing_type():
    assert decode_nodes([{"config": {}}, "junk"]) == [{"type": ""}]
    assert decode_nodes(None) == []


def test_encode_decode_round_trips():
    stored = [
        {"type": "TextColumn", "name": "title", "config": {"sortable": True}},
        {"type": "BadgeColumn", "name": "status"},
    ]
    assert decode_nodes(encode_nodes(stored)) == stored
