"""``Block`` — a page/layout building block.

Where a form :class:`~django_control_components.schemas.layout.Layout` has one
implicit child list, a block declares zero or more **named** slots
(``AppShell`` wants ``topbar`` / ``sidebar`` / ``content`` / ``footer``; a plain
container wants just ``"default"``). That is the one structural difference from
``Layout`` — everything else (fluent ``@setter`` config, ``visible``/``hidden``,
rendering through ``template_name``) is the ordinary :class:`Component` contract.

No concrete blocks are registered yet — this module is foundation for the
layout/chrome blocks that land on top of it (``AppShell``, ``Grid``, ``Sidebar``,
…) and the tree-builder UI that edits them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self

from django.utils.safestring import SafeString, mark_safe

from ..core.component import Component

if TYPE_CHECKING:
    from ..core.context import RenderContext


class Block(Component):
    """A :class:`Component` with named child slots instead of one child list."""

    #: slot names this block accepts children into. A block with no slots
    #: (e.g. a leaf like ``Divider``) leaves this empty.
    slots: ClassVar[tuple[str, ...]] = ()

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self._slots: dict[str, list[Block]] = {slot: [] for slot in self.slots}
        super().__init__(name, **kwargs)

    def fill(self, slot: str, children: list[Block]) -> Self:
        """Set a named slot's children. Raises on an unknown slot or a
        non-``Block`` child — the same posture as ``Tabs.schema()`` for tabs."""
        if slot not in self._slots:
            raise ValueError(
                f"{type(self).__name__} has no slot {slot!r}. Valid: {sorted(self._slots)}"
            )
        for child in children:
            if not isinstance(child, Block):
                raise TypeError(
                    f"{type(self).__name__}.fill({slot!r}, ...) accepts only Block instances"
                )
        self._slots[slot] = list(children)
        return self

    def slot_children(self, slot: str) -> list[Block]:
        return list(self._slots.get(slot, ()))

    def render_slot(self, slot: str, ctx: RenderContext) -> SafeString:
        # Every part is already a SafeString from Component.render.
        parts = [str(child.render(ctx.child(parent=self))) for child in self._slots.get(slot, ())]
        return mark_safe("".join(parts))  # noqa: S308

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["slots"] = {slot: self.render_slot(slot, ctx) for slot in self._slots}
        return data
