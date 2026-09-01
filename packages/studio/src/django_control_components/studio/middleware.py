"""Turn ``django.contrib.messages`` into toasts on htmx responses.

Add to ``MIDDLEWARE`` after ``MessageMiddleware``::

    "django_control_components.studio.middleware.ToastMiddleware",

On an htmx request it drains any pending messages into an ``HX-Trigger``
``dcc:notify`` payload, which ``dcc.js`` renders as a toast — so an ordinary
view's ``messages.success(request, "Saved")`` shows up with no extra code.
Only htmx responses are touched, so a normal page load still renders its
messages the usual way.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse

from .notifications import pending_toasts


class ToastMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if request.headers.get("HX-Request") != "true":
            return response
        toasts = pending_toasts(request)
        if not toasts:
            return response
        try:
            trigger: dict[str, Any] = json.loads(response.headers.get("HX-Trigger", "") or "{}")
        except ValueError:
            trigger = {}
        # dcc.js listens for both; one payload per response is enough in practice
        trigger["dcc:notify"] = toasts[0]
        response.headers["HX-Trigger"] = json.dumps(trigger)
        return response
