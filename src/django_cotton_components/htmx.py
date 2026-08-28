"""The single htmx adapter.

No template in this package contains a literal ``hx-*`` attribute. Every one is
produced here and handed to a template as a pre-built :class:`AttributeBag`
(``{{ htmx_attrs }}``). Migrating to htmx 4 is therefore a change to this file
only. A test greps the template tree to enforce that.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from django.http import HttpResponse
from django.middleware.csrf import get_token

from .core.attributes import AttributeBag

if TYPE_CHECKING:
    from django.http import HttpRequest

HTMX_VERSION = 2
HTMX_SRC = "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js"

Swap = Literal[
    "innerHTML", "outerHTML", "beforebegin", "afterbegin", "beforeend", "afterend", "delete", "none"
]


def _build(
    verb: str,
    url: str,
    *,
    target: str | None,
    swap: Swap,
    trigger: str | None,
    indicator: str | None,
    push_url: bool | str,
    select: str | None,
    sync: str | None,
    headers: dict[str, str] | None,
    values: dict[str, Any] | None,
    include: str | None = None,
) -> AttributeBag:
    bag = AttributeBag()
    bag.set(f"hx-{verb}", url)
    if target:
        bag.set("hx-target", target)
    bag.set("hx-swap", swap)
    if include:
        bag.set("hx-include", include)
    if trigger:
        bag.set("hx-trigger", trigger)
    if indicator:
        bag.set("hx-indicator", indicator)
    if push_url is True:
        bag.set("hx-push-url", "true")
    elif isinstance(push_url, str) and push_url:
        bag.set("hx-push-url", push_url)
    if select:
        bag.set("hx-select", select)
    if sync:
        bag.set("hx-sync", sync)
    if headers:
        bag.set("hx-headers", json.dumps(headers))
    if values:
        bag.set("hx-vals", json.dumps(values))
    return bag


def get(
    url: str,
    *,
    target: str | None = None,
    swap: Swap = "innerHTML",
    trigger: str | None = None,
    indicator: str | None = None,
    push_url: bool | str = False,
    select: str | None = None,
    sync: str | None = None,
    values: dict[str, Any] | None = None,
    include: str | None = None,
) -> AttributeBag:
    return _build(
        "get",
        url,
        target=target,
        swap=swap,
        trigger=trigger,
        indicator=indicator,
        push_url=push_url,
        select=select,
        sync=sync,
        headers=None,
        values=values,
        include=include,
    )


def _mutate(
    verb: str,
    url: str,
    *,
    request: HttpRequest,
    target: str | None,
    swap: Swap,
    trigger: str | None,
    indicator: str | None,
    confirm: str | None,
    values: dict[str, Any] | None,
    select: str | None = None,
) -> AttributeBag:
    bag = _build(
        verb,
        url,
        target=target,
        swap=swap,
        trigger=trigger,
        indicator=indicator,
        push_url=False,
        select=select,
        sync=None,
        headers={"X-CSRFToken": get_token(request)},
        values=values,
    )
    if confirm:
        bag.set("hx-confirm", confirm)
    return bag


def post(
    url: str,
    *,
    request: HttpRequest,
    target: str | None = None,
    swap: Swap = "outerHTML",
    trigger: str | None = None,
    indicator: str | None = None,
    confirm: str | None = None,
    values: dict[str, Any] | None = None,
    select: str | None = None,
) -> AttributeBag:
    return _mutate(
        "post",
        url,
        request=request,
        target=target,
        swap=swap,
        trigger=trigger,
        indicator=indicator,
        confirm=confirm,
        values=values,
        select=select,
    )


def delete(
    url: str,
    *,
    request: HttpRequest,
    target: str | None = None,
    swap: Swap = "outerHTML",
    confirm: str | None = None,
) -> AttributeBag:
    return _mutate(
        "delete",
        url,
        request=request,
        target=target,
        swap=swap,
        trigger=None,
        indicator=None,
        confirm=confirm,
        values=None,
    )


def boost(
    *, enabled: bool = True, target: str | None = None, select: str | None = None
) -> AttributeBag:
    """``hx-boost`` an element for progressive-enhancement navigation.

    Studio pages boost their shell so a save or a nav click swaps a fragment
    instead of reloading the document.
    """
    bag = AttributeBag()
    bag.set("hx-boost", "true" if enabled else "false")
    if target:
        bag.set("hx-target", target)
    if select:
        bag.set("hx-select", select)
    return bag


def oob(value: str | bool = True) -> AttributeBag:
    """Mark a response fragment for an out-of-band swap (``hx-swap-oob``).

    Used when one response updates a second region — e.g. a studio save that
    also refreshes the live navigation. ``value`` is ``True`` or an explicit
    swap spec such as ``"innerHTML:#dcc-nav"``.
    """
    bag = AttributeBag()
    bag.set("hx-swap-oob", "true" if value is True else value)
    return bag


def is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


class response:
    @staticmethod
    def trigger(resp: HttpResponse, events: dict[str, Any] | list[str] | str) -> HttpResponse:
        payload = events if isinstance(events, str) else json.dumps(events)
        resp["HX-Trigger"] = payload
        return resp

    @staticmethod
    def redirect(url: str) -> HttpResponse:
        resp = HttpResponse(status=204)
        resp["HX-Redirect"] = url
        return resp

    @staticmethod
    def refresh() -> HttpResponse:
        resp = HttpResponse(status=204)
        resp["HX-Refresh"] = "true"
        return resp
