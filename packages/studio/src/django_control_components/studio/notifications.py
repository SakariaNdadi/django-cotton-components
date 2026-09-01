"""Create notifications and turn them (and Django messages) into toasts.

Built on the two seams that already work: ``htmx.response.trigger`` (any dict)
and the ``dcc:notify`` / ``dcc:toast`` DOM-event contract in ``dcc.js``. No
Channels / websockets — the ``NotificationBell`` block polls.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone

_MESSAGE_LEVEL_TO_TOAST = {
    "debug": "info",
    "info": "info",
    "success": "success",
    "warning": "warning",
    "error": "error",
}


def notify(
    user: Any,
    title: str,
    *,
    level: str = "info",
    body: str = "",
    url: str = "",
    actor: Any = None,
) -> Any:
    """Persist a :class:`~.models.Notification` for ``user``."""
    from .models import Notification

    return Notification.objects.create(
        user=user, title=title, level=level, body=body, url=url, actor=actor
    )


def unread_count(user: Any) -> int:
    from .models import Notification

    if user is None or not getattr(user, "is_authenticated", False):
        return 0
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def mark_all_read(user: Any) -> int:
    from .models import Notification

    return Notification.objects.filter(user=user, read_at__isnull=True).update(
        read_at=timezone.now()
    )


def pending_toasts(request: Any) -> list[dict[str, str]]:
    """Drain ``django.contrib.messages`` into the toast dict shape so an
    ordinary Django view's ``messages.success(...)`` renders as a toast for
    free. Safe when the messages framework is not installed."""
    try:
        from django.contrib import messages
    except Exception:
        return []
    out: list[dict[str, str]] = []
    for message in messages.get_messages(request):
        out.append(
            {
                "level": _MESSAGE_LEVEL_TO_TOAST.get(message.level_tag, "info"),
                "title": str(message.message),
                "body": "",
                "url": "",
            }
        )
    return out
