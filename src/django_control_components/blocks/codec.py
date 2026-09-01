"""The wire <-> stored codec for a flat list of ``{type, name, config}`` nodes.

Two call sites in the studio builder - the dashboard's widget list and the
resource builder's columns/filters - independently folded ``name`` into
``config.name`` for the wire form and back out for storage. Same transform,
duplicated. This is the one implementation.

Wire form (what the browser's doc store edits): ``{"id": "n0", "type": ...,
"config": {..., "name": <folded in>}}``. Stored form (what a
``DashboardSpec``/``PanelDashboard`` JSONField holds): ``{"type": ..., "name":
..., "config": {...}}`` - ``name`` lifted back out, dropped entirely if unset.
"""

from __future__ import annotations

from typing import Any


def encode_nodes(
    nodes: list[dict[str, Any]] | None, *, id_prefix: str = "n"
) -> list[dict[str, Any]]:
    """Stored ``[{type, name, config}]`` -> wire ``[{id, type, config}]``."""
    out: list[dict[str, Any]] = []
    for index, node in enumerate(nodes or []):
        if not isinstance(node, dict):
            continue
        config = dict(node.get("config") or {})
        if node.get("name"):
            config.setdefault("name", node["name"])
        out.append({"id": f"{id_prefix}{index}", "type": node.get("type", ""), "config": config})
    return out


def decode_node(node: dict[str, Any]) -> dict[str, Any]:
    """Wire ``{type, config: {name, ...}}`` -> stored ``{type, name?, config?}``."""
    result: dict[str, Any] = {"type": node.get("type", "")}
    config = dict(node.get("config") or {})
    name = config.pop("name", None)
    if name:
        result["name"] = name
    if config:
        result["config"] = config
    return result


def decode_nodes(nodes: list[Any] | None) -> list[dict[str, Any]]:
    return [decode_node(node) for node in nodes or [] if isinstance(node, dict)]
