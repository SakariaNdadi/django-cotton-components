from __future__ import annotations

from typing import Any

from ..panels.resource import Resource
from .deserialize import (
    build_infolist_from_spec,
    build_schema_from_spec,
    build_table_from_spec,
)
from .models import DashboardSpec


class DynamicResource(Resource):
    """A :class:`Resource` whose UI comes from a :class:`DashboardSpec` row.

    ``Panel.dynamic()`` binds one URL group to this class and resolves the spec
    per request from the ``<spec_slug>`` URL kwarg.
    """

    spec: DashboardSpec  # set by the bound view via .for_spec()

    @classmethod
    def for_spec(cls, spec: DashboardSpec) -> type[DynamicResource]:
        model = spec.resolve_model()
        return type(
            f"Dynamic{model.__name__}Resource",
            (cls,),
            {
                "spec": spec,
                "model": model,
                "navigation_label": spec.label or None,
                "navigation_icon": spec.nav_icon,
                "navigation_group": spec.nav_group,
                "permission_prefix": spec.permission_prefix or None,
            },
        )

    @classmethod
    def slug(cls) -> str:
        return cls.spec.slug

    @classmethod
    def build_table(cls, *, request: Any) -> Any:
        table = build_table_from_spec(cls.get_queryset(request), cls.spec.table or {})
        return table.id(f"studio-{cls.spec.slug}")

    @classmethod
    def build_schema(cls, *, request: Any) -> Any:
        return build_schema_from_spec(cls.model, cls.spec.schema or {})

    @classmethod
    def build_infolist(cls, *, request: Any) -> Any:
        return build_infolist_from_spec(cls.model, cls.spec.infolist or {})
