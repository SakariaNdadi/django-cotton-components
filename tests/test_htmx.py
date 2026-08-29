from __future__ import annotations

import json

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from django_control_components import htmx


@pytest.fixture
def request_with_csrf():
    return RequestFactory().get("/")


def test_get_builds_expected_attrs():
    bag = htmx.get("/x/", target="#t", swap="outerHTML", push_url=True, trigger="click")
    rendered = str(bag.render())
    assert 'hx-get="/x/"' in rendered
    assert 'hx-target="#t"' in rendered
    assert 'hx-swap="outerHTML"' in rendered
    assert 'hx-push-url="true"' in rendered
    assert 'hx-trigger="click"' in rendered


def test_get_never_carries_csrf():
    assert "X-CSRFToken" not in str(htmx.get("/x/").render())


def test_post_always_injects_csrf(request_with_csrf):
    bag = htmx.post("/save/", request=request_with_csrf, target="#form")
    rendered = str(bag.render())
    assert 'hx-post="/save/"' in rendered
    assert "X-CSRFToken" in rendered
    assert "hx-headers" in rendered


def test_delete_injects_csrf_and_confirm(request_with_csrf):
    rendered = str(htmx.delete("/d/1/", request=request_with_csrf, confirm="Sure?").render())
    assert 'hx-delete="/d/1/"' in rendered
    assert 'hx-confirm="Sure?"' in rendered
    assert "X-CSRFToken" in rendered


def test_response_helpers():
    resp = htmx.response.trigger(HttpResponse(), {"toast": "saved"})
    assert json.loads(resp["HX-Trigger"]) == {"toast": "saved"}

    assert htmx.response.trigger(HttpResponse(), "plain")["HX-Trigger"] == "plain"
    assert htmx.response.redirect("/next/")["HX-Redirect"] == "/next/"
    assert htmx.response.redirect("/next/").status_code == 204
    assert htmx.response.refresh()["HX-Refresh"] == "true"


def test_is_htmx():
    rf = RequestFactory()
    assert htmx.is_htmx(rf.get("/", HTTP_HX_REQUEST="true")) is True
    assert htmx.is_htmx(rf.get("/")) is False


def test_values_serialised():
    rendered = str(htmx.get("/x/", values={"page": 2}).render())
    assert 'hx-vals="{&quot;page&quot;: 2}"' in rendered or "hx-vals" in rendered


def test_boost_builds_attrs():
    rendered = str(htmx.boost(target="#main", select="#main").render())
    assert 'hx-boost="true"' in rendered
    assert 'hx-target="#main"' in rendered
    assert 'hx-select="#main"' in rendered
    assert 'hx-boost="false"' in str(htmx.boost(enabled=False).render())


def test_oob_builds_attrs():
    assert 'hx-swap-oob="true"' in str(htmx.oob().render())
    assert 'hx-swap-oob="innerHTML:#dcc-nav"' in str(htmx.oob("innerHTML:#dcc-nav").render())


def test_get_extras_render():
    bag = htmx.get(
        "/x/", sync="closest form:abort", select="#rows", include="[data-x]:checked"
    ).render()
    rendered = str(bag)
    assert "hx-sync" in rendered
    assert 'hx-select="#rows"' in rendered
    assert "hx-include" in rendered
