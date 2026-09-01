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
    modal_body_template = "django_control_components/actions/_modal_body.html"

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
    def modal(self, value: Schema | Callable[..., Any] | bool = True) -> Self:
        """Open this action in a modal instead of navigating.

        ``.modal(schema)`` renders that schema's form (bound to the record for a
        row action); ``.modal(fn)`` renders ``fn(record=...)`` HTML; ``.modal()``
        is a plain confirm dialog. Distinct from ``.to_url()`` (navigate to a page).
        """
        from ..schemas.schema import Schema as _Schema

        if isinstance(value, _Schema):
            self._config["schema"] = value
        elif callable(value):
            self._config["modal_content"] = value
        self._config["modal"] = True
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

    @setter
    def collapsed(self, value: bool = True) -> Self:
        """Fold this row action into the table's trailing "⋯" menu instead of
        showing it as an inline button."""
        self._config["collapsed"] = value
        return self

    # -- introspection -------------------------------------------

    @property
    def header(self) -> str:
        return self._config.get("label", self.name.replace("_", " ").title())

    @property
    def is_collapsed(self) -> bool:
        return bool(self._config.get("collapsed"))

    @property
    def needs_modal(self) -> bool:
        return bool(
            self._config.get("confirm") or self._config.get("schema") or self._config.get("modal")
        )

    def bind_owner(self, owner_key: str) -> None:
        self._owner_key = owner_key

    # -- authorization ------------------------------------------

    def is_authorized(self, request: HttpRequest, record: Any = None) -> bool:
        rule = self._config.get("authorize", UNSET)
        if rule is UNSET:
            from ..conf import dcc_settings

            return not dcc_settings.ACTIONS_DEFAULT_DENY
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

    def _bulk_url(self, request: HttpRequest | None) -> str:
        """Bulk action URL carrying the table's current filter/search querystring,
        so the endpoint re-scopes ``select_all`` to the same rows the user sees."""
        base = self.url()
        params = request.GET.urlencode() if request is not None else ""
        return f"{base}?{params}" if params else base

    # -- rendering --------------------------------------------

    @property
    def _variant(self) -> str:
        return self._config.get("variant", self._config.get("color", "secondary"))

    def _button(self) -> Any:
        from ..ui import Button

        button = Button.make().label(self.header).variant(self._variant)
        icon = self._config.get("icon", "")
        if icon:
            button.icon(icon)
        button.extra_attributes({"class": "dcc-action"})
        return button

    def render_trigger(
        self, *, record: Any = None, request: HttpRequest | None = None
    ) -> SafeString:
        from ..core.context import RenderContext

        if request is not None and not self.is_visible(request, record):
            return SafeString("")

        ctx = RenderContext(request=request, record=record)
        button = self._button()

        link = self._config.get("link")
        if link is not None:
            button.href(evaluate(link, ctx))
            return button.render(ctx)

        target = f"#dcc-modal-{self._owner_key}"
        action_url = self._bulk_url(request) if self.is_bulk else self.url(record)
        # A bulk trigger has no record; the selected pks and the select-all flag
        # ride along as hidden inputs in the bulk bar (`.dcc-table__bulk`), which
        # htmx resolves via `closest`. Filters/search are baked into `action_url`.
        include = "closest .dcc-table__bulk" if self.is_bulk else None
        if self.needs_modal:
            attrs = htmx_adapter.get(action_url, target=target, swap="innerHTML", include=include)
        elif request is not None and not self.is_bulk:
            attrs = htmx_adapter.post(
                action_url, request=request, target="closest tr", swap="outerHTML"
            )
        else:
            attrs = htmx_adapter.get(action_url, target=target, include=include)
        button.attributes(attrs)
        return button.render(ctx)

    def row_click_attrs(self, *, record: Any, request: HttpRequest | None = None) -> dict[str, str]:
        """``data-*`` attributes for a table row whose whole surface triggers this
        action. Read by dcc.js's delegated row-click handler (kept off ``hx-*`` so
        a button *inside* the row still fires independently). Supports ``.to_url``
        (navigate) and modal actions; anything else navigates to nowhere."""
        from ..core.context import RenderContext

        if request is not None and not self.is_visible(request, record):
            return {}
        ctx = RenderContext(request=request, record=record)
        link = self._config.get("link")
        if link is not None:
            return {"data-dcc-href": str(evaluate(link, ctx))}
        if self.needs_modal:
            return {
                "data-dcc-action": self.url(record),
                "data-dcc-action-target": f"#dcc-modal-{self._owner_key}",
                "data-dcc-action-swap": "innerHTML",
            }
        return {}

    def render_modal(
        self, *, request: HttpRequest, records: Any, form_html: SafeString | str = ""
    ) -> SafeString:
        from django.db.models import QuerySet

        from ..core.context import RenderContext
        from ..ui import Button, Modal

        select_all = isinstance(records, QuerySet)
        first = None if select_all else (records[0] if records else None)
        ctx = RenderContext(request=request, record=first)
        cancel = (
            Button.make()
            .label("Cancel")
            .variant("secondary")
            .attributes({"x-on:click": "open = false"})
        )
        confirm = Button.make().label(self.header).variant(self._variant).type("submit")
        # carry the current filter querystring so the POST re-derives the same set
        post_url = self.url(first if first and not self.is_bulk else None)
        if select_all:
            filter_qs = request.GET.urlencode()
            post_url = f"{post_url}{'&' if '?' in post_url else '?'}select_all=1&{filter_qs}"
        body = render_to_string(
            self.modal_body_template,
            {
                "description": self._config.get("modal_description", ""),
                "form_html": form_html,
                "record_ids": [] if select_all else [r.pk for r in records],
                "select_all": select_all,
                "cancel_button": cancel.render(ctx),
                "confirm_button": confirm.render(ctx),
                "post_attrs": htmx_adapter.post(
                    post_url,
                    request=request,
                    target=f"#dcc-modal-{self._owner_key}",
                    swap="innerHTML",
                ),
            },
            request=request,
        )
        modal = (
            Modal.make()
            .heading(self._config.get("modal_heading", self.header))
            .body(SafeString(body))
        )
        return modal.render(ctx)

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
