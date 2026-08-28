"""Live per-field validation endpoint for ``.live()`` fields.

A schema is addressed by a registered key, never by an import path from the
client. The endpoint binds the schema's form to the partial POST data, runs
``full_clean``, and returns just the requested field's re-rendered wrapper.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import Http404, HttpRequest, HttpResponse
from django.views import View

if TYPE_CHECKING:
    from .schema import Schema

_SCHEMAS: dict[str, Schema] = {}


def register_schema(key: str, schema: Schema) -> None:
    _SCHEMAS[key] = schema


def clear_schemas() -> None:
    _SCHEMAS.clear()


class SchemaValidateView(View):
    def post(self, request: HttpRequest, schema_key: str) -> HttpResponse:
        schema = _SCHEMAS.get(schema_key)
        if schema is None:
            raise Http404("Unknown schema")
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
