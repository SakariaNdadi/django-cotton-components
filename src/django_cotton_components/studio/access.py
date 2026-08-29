"""Access rules shared by the nav builder, the studio views and the panel pages.

The one invariant: **the studio grants visibility, never authorization.** A
``can_see`` grant can only hide things; data access stays ``Resource.can()`` →
``user.has_perm``. Nothing configured in the studio widens a Django permission.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.http import HttpRequest

#: permission that lets a user open the builder UI (distinct from the model
#: permissions that gate the data a built resource touches)
STUDIO_PERMISSION = "dcc_studio.use_studio"


def can_see(user: Any, obj: Any) -> bool:
    """Thin, stable wrapper over ``AccessControlled.is_visible_to`` so callers do
    not import the model."""
    return bool(obj.is_visible_to(user))


def can_use_studio(request: HttpRequest | None) -> bool:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    return bool(user.is_superuser or user.has_perm(STUDIO_PERMISSION))


def require_studio(request: HttpRequest) -> bool:
    """Panel guard: raise ``LoginRequired`` for an anonymous user, deny others
    without the studio permission."""
    from ..panels.guards import LoginRequired

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        raise LoginRequired
    return can_use_studio(request)
