"""Phase 8: the Notification model, notify(), the polling endpoint, the
messages -> toast bridge and the NotificationBell block."""

from __future__ import annotations

import pytest
from django.contrib import messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls import include, path

from django_control_components.blocks import BLOCK_TYPES, NotificationBell
from django_control_components.core.context import RenderContext
from django_control_components.panels import Panel
from django_control_components.studio.middleware import ToastMiddleware
from django_control_components.studio.models import Notification
from django_control_components.studio.notifications import (
    mark_all_read,
    notify,
    pending_toasts,
    unread_count,
)

pytestmark = pytest.mark.django_db

panel = Panel("s").path("s").studio().auth(lambda r: True)
urlpatterns = [panel.mount(), path("studio/", include("django_control_components.studio.urls"))]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__


# -- model + helpers --------------------------------------------


def test_notify_persists_and_unread_count_tracks_it(django_user_model):
    user = django_user_model.objects.create_user("u")
    notify(user, "Deploy done", level="success", url="/x/")
    notify(user, "Second")
    assert unread_count(user) == 2
    assert mark_all_read(user) == 2
    assert unread_count(user) == 0


def test_unread_count_zero_for_anonymous():
    from django.contrib.auth.models import AnonymousUser

    assert unread_count(AnonymousUser()) == 0


# -- polling endpoint -----------------------------------------


def test_endpoint_returns_unread_and_items(client, urlconf, django_user_model):
    user = django_user_model.objects.create_user("u", password="x")
    notify(user, "Hi")
    client.force_login(user)
    data = client.get("/studio/notifications/").json()
    assert data["unread"] == 1
    assert data["items"][0]["title"] == "Hi"


def test_endpoint_rejects_anonymous(client, urlconf):
    assert client.get("/studio/notifications/").status_code == 403


def test_endpoint_post_marks_all_read(client, urlconf, django_user_model):
    user = django_user_model.objects.create_user("u", password="x")
    notify(user, "Hi")
    client.force_login(user)
    assert client.post("/studio/notifications/").json()["unread"] == 0
    assert Notification.objects.filter(user=user, read_at__isnull=True).count() == 0


# -- messages -> toast bridge -------------------------------


def _request_with_message(text="Saved", *, htmx=True):
    request = RequestFactory().get("/x/", HTTP_HX_REQUEST="true" if htmx else "")
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)
    messages.success(request, text)
    return request


def test_pending_toasts_drains_django_messages():
    toasts = pending_toasts(_request_with_message("Done"))
    assert toasts == [{"level": "success", "title": "Done", "body": "", "url": ""}]


def test_toast_middleware_adds_hx_trigger_on_htmx_responses():
    from django.http import HttpResponse

    request = _request_with_message("Saved")
    mw = ToastMiddleware(lambda r: HttpResponse("ok"))
    response = mw(request)
    assert "dcc:notify" in response.headers["HX-Trigger"]
    assert "Saved" in response.headers["HX-Trigger"]


def test_toast_middleware_ignores_non_htmx_responses():
    from django.http import HttpResponse

    request = _request_with_message("Saved", htmx=False)
    response = ToastMiddleware(lambda r: HttpResponse("ok"))(request)
    assert "HX-Trigger" not in response.headers


# -- NotificationBell block ---------------------------------


def test_bell_is_registered_and_reverses_the_endpoint(urlconf):
    assert "NotificationBell" in BLOCK_TYPES.names()
    html = str(NotificationBell.make().render(RenderContext(request=None)))
    assert 'data-endpoint="/studio/notifications/"' in html
    assert "dccBell()" in html


def test_bell_endpoint_prop_overrides_the_default(urlconf):
    html = str(NotificationBell.make().endpoint("/custom/").render(RenderContext(request=None)))
    assert 'data-endpoint="/custom/"' in html
