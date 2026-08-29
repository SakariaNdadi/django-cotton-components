"""One structured navigation tree per panel, merging code and stored items.

Sources, in order:

* code ``Resource`` classes and code ``PanelPage`` s on the panel;
* enabled ``DashboardSpec`` / ``PanelDashboard`` rows (studio resources /
  dashboards), access-filtered by ``AccessControlled.is_visible_to``;
* ``NavItem`` rows for the panel — a two-level tree the studio edits.

A studio item pointing at a resource the user lacks ``view_`` permission for is
dropped here (and still 403s if hit directly): the studio controls visibility,
never authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from django.urls import NoReverseMatch, reverse

if TYPE_CHECKING:
    from django.http import HttpRequest

    from .panel import Panel


@dataclass
class NavNode:
    label: str
    url: str = ""
    icon: str = ""
    group: str = ""
    active: bool = False
    external: bool = False
    children: list[NavNode] = field(default_factory=list)

    @property
    def is_heading(self) -> bool:
        return not self.url and not self.external


def build_nav(panel: Panel, request: HttpRequest) -> list[NavNode]:
    nodes = _auto_nodes(panel, request)
    nodes += _stored_nodes(panel, request)
    _mark_active(nodes, getattr(request, "path", "") or "")
    return _group(nodes)


def _auto_nodes(panel: Panel, request: HttpRequest) -> list[NavNode]:
    """The flat items ``Panel.navigation`` already computes, as ``NavNode`` s."""
    return [
        NavNode(
            label=item["label"],
            url=item.get("url", ""),
            icon=item.get("icon", ""),
            group=item.get("group", ""),
        )
        for item in panel.navigation(request)
    ]


def _stored_nodes(panel: Panel, request: HttpRequest) -> list[NavNode]:
    try:
        from ..studio.models import NavItem
    except Exception:
        return []

    user = getattr(request, "user", None)
    rows = list(
        NavItem.objects.filter(panel=panel.name, is_enabled=True, parent__isnull=True)
        .prefetch_related("children")
        .order_by("order", "pk")
    )
    out: list[NavNode] = []
    for row in rows:
        node = _navitem_node(row, panel, request, user)
        if node is None:
            continue
        for child in row.children.filter(is_enabled=True).order_by("order", "pk"):
            child_node = _navitem_node(child, panel, request, user)
            if child_node is not None:
                node.children.append(child_node)
        # a heading with no visible children and no url is noise
        if node.is_heading and not node.children:
            continue
        out.append(node)
    return out


def _navitem_node(row: Any, panel: Panel, request: HttpRequest, user: Any) -> NavNode | None:
    if not row.is_visible_to(user):
        return None
    url, external = _resolve_target(row, panel, request)
    if row.target_kind != row.Kind.GROUP and not url:
        return None
    return NavNode(
        label=row.label,
        url=url,
        icon=row.icon,
        group="",
        external=external or row.open_in_new_tab,
    )


def _resolve_target(row: Any, panel: Panel, request: HttpRequest) -> tuple[str, bool]:
    kind, target = row.target_kind, row.target
    ns = panel.namespace
    try:
        if kind == row.Kind.GROUP:
            return "", False
        if kind == row.Kind.URL:
            return target, target.lower().startswith(("http://", "https://"))
        if kind == row.Kind.URL_NAME:
            return reverse(target), False
        if kind == row.Kind.RESOURCE:
            if not _can_view_resource(panel, request, target):
                return "", False
            return reverse(f"{ns}:{target}-list"), False
        if kind == row.Kind.SPEC:
            if not _can_view_spec(request, target):
                return "", False
            return reverse(f"{ns}:studio-list", kwargs={"spec_slug": target}), False
        if kind == row.Kind.DASHBOARD:
            return reverse(f"{ns}:studio-dashboard", kwargs={"dash_slug": target}), False
    except NoReverseMatch:
        return "", False
    return "", False


def _can_view_resource(panel: Panel, request: HttpRequest, slug: str) -> bool:
    for resource in getattr(panel, "_resources", []):
        if resource.slug() == slug:
            return bool(resource.can(request, "view"))
    return False


def _can_view_spec(request: HttpRequest, slug: str) -> bool:
    try:
        from ..studio.models import DashboardSpec
        from ..studio.resource import DynamicResource
    except ModuleNotFoundError:
        return False

    spec = DashboardSpec.objects.filter(slug=slug, is_enabled=True).first()
    if spec is None:
        return False
    return bool(DynamicResource.for_spec(spec).can(request, "view"))


def _mark_active(nodes: list[NavNode], path: str) -> None:
    best: NavNode | None = None
    best_len = 0
    stack = list(nodes)
    while stack:
        node = stack.pop()
        stack.extend(node.children)
        if not node.url or node.external:
            continue
        if path.startswith(node.url) and len(node.url) > best_len:
            best, best_len = node, len(node.url)
    if best is not None:
        best.active = True


def _group(nodes: list[NavNode]) -> list[NavNode]:
    grouped: dict[str, NavNode] = {}
    ordered: list[NavNode] = []
    for node in nodes:
        if not node.group:
            ordered.append(node)
            continue
        heading = grouped.get(node.group)
        if heading is None:
            heading = NavNode(label=node.group)
            grouped[node.group] = heading
            ordered.append(heading)
        node.group = ""
        heading.children.append(node)
    return ordered
