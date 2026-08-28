"""Action addressing.

Security-critical. The client only ever sends an *owner key* and an *action
name*, both opaque strings registered at import/render time. It never sends an
import path, a model label, or a callable. An unknown key is a 404, not an
error page.

An owner (a table, later a resource) knows how to produce the queryset the
action is allowed to touch — used to re-scope row and bulk targets so a tampered
pk cannot reach a row the user was never shown.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

    from .action import Action


class ActionOwner(Protocol):
    @property
    def key(self) -> str: ...

    def get_action_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        """The rows this owner currently exposes — the scope for its actions."""

    def get_actions(self) -> dict[str, Action]: ...


class _Registry:
    def __init__(self) -> None:
        self._owners: dict[str, ActionOwner] = {}

    def register(self, owner: ActionOwner) -> None:
        self._owners[owner.key] = owner

    def resolve(self, owner_key: str, action_name: str) -> tuple[ActionOwner, Action] | None:
        owner = self._owners.get(owner_key)
        if owner is None:
            return None
        action = owner.get_actions().get(action_name)
        if action is None:
            return None
        return owner, action

    def clear(self) -> None:
        self._owners.clear()


registry = _Registry()
