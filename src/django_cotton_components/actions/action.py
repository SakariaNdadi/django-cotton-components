from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import SafeString

from .. import htmx as htmx_adapter
from ..core.component import UNSET, setter
from ..core.evaluate import evaluate

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest

    from ..schemas.schema import Schema


class Action:
    is_bulk = False
    trigger_template = "django_cotton_components/actions/trigger.html"
    modal_template = "django_cotton_components/actions/modal.html"

    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self._config: dict[str, Any] = {}
        self._owner_key: str | None = None
        for key, value in kwargs.items():
            method = getattr(type(self), key, None)
            if method is None or not getattr(method, "__dcc_setter__", False):
                raise TypeError(f"{type(self).__name__} has no setter {key!r}")
            getattr(self, key)(value)

    @classmethod
    def make(cls, name: str, **kwargs: Any) -> Self:
        return cls(name, **kwargs)

    # -- setters ----------------------------------------------------

    @setter
    def label(self, value: str) -> Self:
        self._config["label"] = value
        return self

    @setter
    def icon(self, value: str) -> Self:
        self._config["icon"] = value
        return self

    @setter
    def color(self, value: str) -> Self:
        self._config["color"] = value
        return self

    @setter
    def variant(self, value: str) -> Self:
        self._config["variant"] = value
        return self

    @setter
    def authorize(self, value: str | Callable[..., bool]) -> Self:
        self._config["authorize"] = value
        return self

    @setter
    def requires_confirmation(self, value: bool = True) -> Self:
        self._config["confirm"] = value
        return self

    @setter
    def modal_heading(self, value: str) -> Self:
        self._config["modal_heading"] = value
        return self

    @setter
    def modal_description(self, value: str) -> Self:
        self._config["modal_description"] = value
        return self

    @setter
    def schema(self, value: Schema) -> Self:
        self._config["schema"] = value
        return self

    @setter
    def action(self, fn: Callable[..., Any]) -> Self:
        self._config["callback"] = fn
        return self

    @setter
    def success_notification(self, value: str) -> Self:
        self._config["success_notification"] = value
        return self

    @setter
    def visible(self, value: bool | Callable[..., bool]) -> Self:
        self._config["visible"] = value
        return self

    @setter
    def to_url(self, value: str | Callable[..., str]) -> Self:
        """Render as a plain link instead of an htmx trigger (e.g. an Edit page)."""
        self._config["link"] = value
        return self

    # -- introspection -------------------------------------------

    @property
    def header(self) -> str:
        return self._config.get("label", self.name.replace("_", " ").title())

    @property
    def needs_modal(self) -> bool:
        return bool(self._config.get("confirm") or self._config.get("schema"))

    def bind_owner(self, owner_key: str) -> None:
        self._owner_key = owner_key

    # -- authorization ------------------------------------------

    def is_authorized(self, request: HttpRequest, record: Any = None) -> bool:
        rule = self._config.get("authorize", UNSET)
        if rule is UNSET:
            return True
        if isinstance(rule, str):
            user = getattr(request, "user", None)
            return bool(user and user.has_perm(rule, record))
        from ..core.context import RenderContext

        return bool(evaluate(rule, RenderContext(request=request, record=record)))

    def is_visible(self, request: HttpRequest, record: Any = None) -> bool:
        if not self.is_authorized(request, record):
            return False
        rule = self._config.get("visible", UNSET)
        if rule is UNSET:
            return True
        from ..core.context import RenderContext

        return bool(evaluate(rule, RenderContext(request=request, record=record)))

    # -- urls --------------------------------------------------

    def url(self, record: Any = None) -> str:
        assert self._owner_key is not None, "Action not bound to an owner"
        base = reverse(
            "dcc:action",
            kwargs={"owner_key": self._owner_key, "action_name": self.name},
        )
        if record is not None and not self.is_bulk:
            return f"{base}?record={record.pk}"
        return base

    # -- rendering --------------------------------------------

    def render_trigger(
        self, *, record: Any = None, request: HttpRequest | None = None
    ) -> SafeString:
        if request is not None and not self.is_visible(request, record):
            return SafeString("")

        link = self._config.get("link")
        if link is not None:
            from ..core.context import RenderContext

            href = evaluate(link, RenderContext(request=request, record=record))
            data = {
                "label": self.header,
                "icon": self._config.get("icon", ""),
                "variant": self._config.get("variant", self._config.get("color", "secondary")),
                "href": href,
            }
            return SafeString(render_to_string(self.trigger_template, data, request=request))

        target = f"#dcc-modal-{self._owner_key}"
        if self.needs_modal:
            attrs = htmx_adapter.get(self.url(record), target=target, swap="innerHTML")
        elif request is not None:
            attrs = htmx_adapter.post(
                self.url(record), request=request, target="closest tr", swap="outerHTML"
            )
        else:
            attrs = htmx_adapter.get(self.url(record), target=target)
        data = {
            "label": self.header,
            "icon": self._config.get("icon", ""),
            "variant": self._config.get("variant", self._config.get("color", "secondary")),
            "htmx_attrs": attrs,
        }
        return SafeString(render_to_string(self.trigger_template, data, request=request))

    def render_modal(
        self, *, request: HttpRequest, records: list[Any], form_html: SafeString | str = ""
    ) -> SafeString:
        data = {
            "owner_key": self._owner_key,
            "action_name": self.name,
            "heading": self._config.get("modal_heading", self.header),
            "description": self._config.get("modal_description", ""),
            "confirm_label": self.header,
            "form_html": form_html,
            "post_attrs": htmx_adapter.post(
                self.url(records[0] if records and not self.is_bulk else None),
                request=request,
                target=f"#dcc-modal-{self._owner_key}",
                swap="innerHTML",
            ),
            "record_ids": [r.pk for r in records],
        }
        return SafeString(render_to_string(self.modal_template, data, request=request))

    # -- execution -------------------------------------------

    def run(self, request: HttpRequest, records: list[Any], data: dict[str, Any]) -> Any:
        callback = self._config.get("callback")
        if callback is None:
            return None
        from ..core.evaluate import _param_names

        params = _param_names(callback)
        kwargs: dict[str, Any] = {}
        if "request" in params:
            kwargs["request"] = request
        if "user" in params:
            kwargs["user"] = getattr(request, "user", None)
        if "data" in params:
            kwargs["data"] = data
        if self.is_bulk:
            if "records" in params:
                kwargs["records"] = records
            return callback(**kwargs)
        if "record" in params:
            kwargs["record"] = records[0] if records else None
        return callback(**kwargs)

    def success_message(self) -> str:
        return self._config.get("success_notification", f"{self.header} done.")


class BulkAction(Action):
    is_bulk = True
