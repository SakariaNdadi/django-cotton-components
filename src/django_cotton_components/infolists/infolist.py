from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from django.template.loader import render_to_string
from django.utils.safestring import SafeString

from ..core.context import RenderContext
from .entries import TextEntry

if TYPE_CHECKING:
    from django.db.models import Model
    from django.http import HttpRequest

    from ..core.component import Component


class Infolist:
    """A declarative read schema. ``Infolist.make().schema([...])`` or, with no
    schema, one :class:`TextEntry` per model field."""

    template_name = "django_cotton_components/infolists/infolist.html"

    def __init__(self) -> None:
        self._components: list[Component] = []
        self._model: type[Model] | None = None

    @classmethod
    def make(cls) -> Self:
        return cls()

    def model(self, model: type[Model]) -> Self:
        self._model = model
        return self

    def schema(self, components: list[Component]) -> Self:
        self._components = list(components)
        return self

    components = schema

    def _effective(self) -> list[Component]:
        if self._components:
            return self._components
        if self._model is None:
            return []
        return [
            TextEntry.make(f.name).label(f.verbose_name.title()) for f in self._model._meta.fields
        ]

    def render(self, *, request: HttpRequest | None = None, record: Any = None) -> SafeString:
        ctx = RenderContext(request=request, record=record, operation="view")
        children = "".join(str(c.render(ctx.child(record=record))) for c in self._effective())
        html = render_to_string(
            self.template_name, {"children_html": SafeString(children)}, request=request
        )
        return SafeString(html)
