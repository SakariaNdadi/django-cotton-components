"""A Resource wires a model to list / create / edit / view pages.

Filament-inspired, deliberately smaller: no Livewire underneath means no
server-held component state, so this is CRUD scaffolding on plain Django CBVs,
not an "admin replacement". It coexists with ``django.contrib.admin`` by living
under its own URL prefix and touching none of admin's machinery.

Subclass and override ``build_schema`` / ``build_table`` / ``get_queryset``.
Everything is a method (never a class attribute) so per-request state cannot
leak between requests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.utils.text import slugify

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from django.http import HttpRequest

    from ..schemas.schema import Schema
    from ..tables.table import Table


class Resource:
    model: ClassVar[type[Model]]
    form_class: ClassVar[type | None] = None

    #: permission prefix; defaults to the model's app_label.model_name
    permission_prefix: ClassVar[str | None] = None
    navigation_label: ClassVar[str | None] = None
    navigation_icon: ClassVar[str] = ""
    navigation_group: ClassVar[str] = ""

    # -- identity -------------------------------------------------

    @classmethod
    def slug(cls) -> str:
        return slugify(cls.model._meta.model_name or cls.__name__)

    @classmethod
    def label(cls) -> str:
        return cls.navigation_label or str(cls.model._meta.verbose_name_plural).title()

    @classmethod
    def perm(cls, action: str) -> str:
        prefix = cls.permission_prefix or (
            f"{cls.model._meta.app_label}.{action}_{cls.model._meta.model_name}"
        )
        return prefix if "." in prefix else f"{cls.model._meta.app_label}.{prefix}"

    # -- data ---------------------------------------------------

    @classmethod
    def get_queryset(cls, request: HttpRequest) -> QuerySet[Any]:
        return cls.model._default_manager.all()

    @classmethod
    def get_form_class(cls) -> type:
        if cls.form_class is not None:
            return cls.form_class
        from django.forms import modelform_factory

        return modelform_factory(cls.model, fields="__all__")

    # -- UI (override these) ------------------------------------

    @classmethod
    def build_schema(cls, *, request: HttpRequest) -> Schema:
        from ..schemas.schema import Schema

        return Schema.make().form(cls.get_form_class())

    @classmethod
    def build_table(cls, *, request: HttpRequest) -> Table:
        from ..tables.columns import TextColumn
        from ..tables.table import Table

        model_fields = [
            f.name for f in cls.model._meta.fields if f.name != "id" and not f.is_relation
        ][:5]
        table = Table.make(cls.get_queryset(request)).id(cls.slug())
        table.columns([TextColumn.make(name).sortable().searchable() for name in model_fields])
        return table

    # -- authorization ---------------------------------------

    @classmethod
    def can(cls, request: HttpRequest, action: str, obj: Model | None = None) -> bool:
        user = getattr(request, "user", None)
        if user is None:
            return False
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        # model-level check; object-level auth is opt-in by overriding can()
        return user.has_perm(cls.perm(action))
