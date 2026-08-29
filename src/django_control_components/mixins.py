"""View mixins for plain Django class-based views."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.forms import BaseForm
    from django.http import HttpResponse

    from .schemas.schema import Schema


class SchemaFormMixin:
    """Drive a ``FormView``/``CreateView``/``UpdateView`` from a :class:`Schema`.

    Set ``schema`` (an instance) or override ``get_schema()``. The mixin uses the
    schema's Django form for validation and hands the bound form back to the
    schema for rendering.
    """

    schema: Schema | None = None

    def get_schema(self) -> Schema:
        if self.schema is None:
            raise ValueError(f"{type(self).__name__} needs a `schema` or `get_schema()`")
        return self.schema

    def get_form_class(self) -> type[BaseForm]:
        return self.get_schema().get_form_class()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context_data(**kwargs)  # type: ignore[misc]
        schema = self.get_schema()
        context["schema"] = schema
        context["schema_html"] = schema.render(
            request=getattr(self, "request", None),
            form=context["form"],
            record=getattr(self, "object", None),
        )
        return context

    def form_valid(self, form: BaseForm) -> HttpResponse:
        response: HttpResponse = super().form_valid(form)  # type: ignore[misc]
        instance = getattr(self, "object", None)
        schema = self.get_schema()
        if instance is not None and schema.image_specs():
            schema.process_images(instance)
        return response
