"""Panel access guards.

A guard is ``Callable[[HttpRequest], bool]`` passed to ``Panel.auth(...)``.
Returning ``False`` denies with ``PermissionDenied`` (403). Raising
:class:`LoginRequired` instead makes the panel page redirect an anonymous user
to the login page - ``LoginRequired`` is deliberately **not** a
``PermissionDenied`` subclass so the page can tell the two apart.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest


class LoginRequired(Exception):
    """Raised by a guard when the request is anonymous - the page turns this
    into a redirect to ``settings.LOGIN_URL`` (or ``Panel.login_url``)."""


def login_required(request: HttpRequest) -> bool:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        raise LoginRequired
    return True


def staff_required(request: HttpRequest) -> bool:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        raise LoginRequired
    return bool(user.is_staff)


def permission_required(perm: str) -> Callable[[HttpRequest], bool]:
    def guard(request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            raise LoginRequired
        return bool(user.has_perm(perm))

    return guard


def group_required(*names: str) -> Callable[[HttpRequest], bool]:
    wanted = set(names)

    def guard(request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            raise LoginRequired
        if user.is_superuser:
            return True
        return wanted.issubset(set(user.groups.values_list("name", flat=True)))

    return guard
