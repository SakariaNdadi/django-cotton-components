"""Live per-field validation endpoint for ``.live()`` fields.

A schema is addressed by a registered key, never by an import path from the
client. The endpoint binds the schema's form to the partial POST data, runs
``full_clean``, and returns just the requested field's re-rendered wrapper.

Access: a registration may carry an ``authorize`` predicate
(``Callable[[HttpRequest], bool]``) — typically the owning view's permission
check. With none given the endpoint still requires an authenticated user, so a
dormant registration cannot echo rendered markup to anonymous callers.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.views import View

if TYPE_CHECKING:
    from .schema import Schema

Authorize = Callable[[HttpRequest], bool]

_SCHEMAS: dict[str, tuple[Schema, Authorize | None]] = {}


def register_schema(key: str, schema: Schema, *, authorize: Authorize | None = None) -> None:
    _SCHEMAS[key] = (schema, authorize)


def clear_schemas() -> None:
    _SCHEMAS.clear()


def _is_authenticated(request: HttpRequest) -> bool:
    user = getattr(request, "user", None)
    return bool(user is not None and user.is_authenticated)


class SchemaValidateView(View):
    def post(self, request: HttpRequest, schema_key: str) -> HttpResponse:
        entry = _SCHEMAS.get(schema_key)
        if entry is None:
            raise Http404("Unknown schema")
        schema, authorize = entry

        allowed = authorize(request) if authorize is not None else _is_authenticated(request)
        if not allowed:
            raise PermissionDenied

        field_name = request.POST.get("_field")
        if not field_name:
            return HttpResponse(status=400)

        form = schema.build_form(data=request.POST)
        form.is_valid()

        from ..core.context import RenderContext

        for field in schema.iter_fields():
            if field.name == field_name:
                ctx = RenderContext(request=request, form=form)
                return HttpResponse(field.render(ctx))
        raise Http404("Unknown field")
