"""The notification-bell polling endpoint. Any signed-in user, not just studio
users — so it does not extend :class:`StudioView`."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views import View

from ..notifications import mark_all_read, unread_count

_RECENT = 10


class NotificationsApi(View):
    def _deny(self) -> JsonResponse:
        return JsonResponse({"detail": "authentication required"}, status=403)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return self._deny()
        from ..models import Notification

        items = [
            {
                "id": n.pk,
                "level": n.level,
                "title": n.title,
                "body": n.body,
                "url": n.url,
                "read": n.read_at is not None,
                "created_at": n.created_at.isoformat(),
            }
            for n in Notification.objects.filter(user=user)[:_RECENT]
        ]
        return JsonResponse({"unread": unread_count(user), "items": items})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return self._deny()
        mark_all_read(user)
        return JsonResponse({"unread": 0})
