"""Generate a complete, immediately-working spec from a model.

``scaffold_spec(model)`` is the "django admin just starts up" moment - one call
produces a ``{table, schema, infolist}`` that renders a usable list + create +
edit + view with sensible columns, filters and sorting, zero clicks. It is used
by the ``dcc_scaffold`` command and by the studio's "Add model" button.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .introspect import SENSITIVE_FIELDS, describe_model

if TYPE_CHECKING:
    from django.db.models import Model

_MAX_TABLE_COLUMNS = 6


def _editable_field_names(model: type[Model]) -> list[str]:
    names: list[str] = []
    for field in model._meta.get_fields():
        if not getattr(field, "concrete", False):
            continue
        if field.name in SENSITIVE_FIELDS:
            continue
        if getattr(field, "primary_key", False):
            continue
        if not getattr(field, "editable", False):
            continue  # AutoField, auto_now / auto_now_add
        if field.many_to_many:
            continue  # a schema spec node has no m2m widget yet
        names.append(field.name)
    return names


def scaffold_spec(model: type[Model], *, request: Any = None) -> dict[str, Any]:
    fields = describe_model(model, request)
    by_name = {row["name"]: row for row in fields}

    display = [row for row in fields if row["name"] not in {"id", "pk"}]
    columns = [
        {
            "type": row["column_type"],
            "name": row["name"],
            "config": _column_config(row),
        }
        for row in display[:_MAX_TABLE_COLUMNS]
    ]

    filters: list[dict[str, Any]] = []
    for row in fields:
        if row["choices"]:
            filters.append(
                {
                    "type": "SelectFilter",
                    "name": row["name"],
                    "config": {"options": row["choices"]},
                }
            )
        elif row["kind"] in {"BooleanField", "NullBooleanField"}:
            filters.append({"type": "TernaryFilter", "name": row["name"]})

    default_sort = next(
        (f"-{row['name']}" for row in fields if row["kind"] in {"DateField", "DateTimeField"}),
        None,
    )

    table: dict[str, Any] = {"columns": columns, "searchable": True}
    if filters:
        table["filters"] = filters
    if default_sort:
        table["default_sort"] = default_sort

    editable = _editable_field_names(model)
    schema = {
        "fields": editable,
        "layout": [
            {
                "type": "Section",
                "name": "Details",
                "children": [
                    {"type": by_name.get(name, {}).get("field_type", "TextInput"), "name": name}
                    for name in editable
                ],
            }
        ],
    }

    infolist = {"entries": [{"type": row["entry_type"], "name": row["name"]} for row in display]}

    return {"table": table, "schema": schema, "infolist": infolist}


def _column_config(row: dict[str, Any]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if not row["is_relation"]:
        config["sortable"] = True
    if row["searchable"]:
        config["searchable"] = True
    if row["kind"] == "TextField":
        config["limit"] = 60
    return config


def scaffold_dashboard(models: list[type[Model]], *, request: Any = None) -> dict[str, Any]:
    """A stat widget per model plus one chart over the first model with a
    ``choices`` field."""
    widgets: list[dict[str, Any]] = []
    for model in models:
        label = f"{model._meta.app_label}.{model._meta.model_name}"
        widgets.append(
            {
                "type": "StatWidget",
                "name": str(model._meta.verbose_name_plural).title(),
                "config": {"query": {"model": label, "aggregate": "count"}},
            }
        )
        if not any(w["type"] == "ChartWidget" for w in widgets):
            choice_field = next(
                (row["name"] for row in describe_model(model, request) if row["choices"]),
                None,
            )
            if choice_field:
                plural = str(model._meta.verbose_name_plural).title()
                widgets.append(
                    {
                        "type": "ChartWidget",
                        "name": f"{plural} by {choice_field}",
                        "config": {
                            "kind": "bar",
                            "query": {
                                "model": label,
                                "aggregate": "count",
                                "group_by": choice_field,
                            },
                        },
                    }
                )
    return {"widgets": widgets}


#: known table column classes an ejected file may import from ``tables``
_COLUMN_IMPORTS = {
    "TextColumn",
    "BadgeColumn",
    "BooleanColumn",
    "DateColumn",
    "ImageColumn",
}


def eject_to_python(label: str, spec: dict[str, Any], *, class_name: str | None = None) -> str:
    """Render a stored ``{table, schema, infolist}`` spec as a Python
    ``Resource`` subclass a team can drop into version control and edit freely
    — the escape hatch out of no-code.

    Only the list table is materialised as code; the create/edit schema and the
    infolist fall back to the framework defaults, which a dev then overrides by
    hand. The generated module imports nothing from the studio package.
    """
    app_label, _, model_name = label.partition(".")
    cls = class_name or f"{model_name}Resource"
    columns = (spec.get("table") or {}).get("columns", [])

    used = {c.get("type", "TextColumn") for c in columns} & _COLUMN_IMPORTS
    used.add("Table")
    imports = ", ".join(sorted(used))

    lines = [
        '"""Generated by `manage.py dcc_scaffold --eject`. Move into your app and edit."""',
        "",
        "from django.apps import apps",
        "",
        "from django_control_components.panels import Resource",
        f"from django_control_components.tables import {imports}",
        "",
        "",
        f"class {cls}(Resource):",
        f'    model = apps.get_model("{app_label}", "{model_name}")',
        "",
        "    @classmethod",
        "    def build_table(cls, *, request):",
        "        table = Table.make(cls.get_queryset(request)).id(cls.slug())",
        "        table.columns([",
    ]
    for column in columns:
        col_type = column.get("type", "TextColumn")
        if col_type not in _COLUMN_IMPORTS:
            col_type = "TextColumn"
        name = column.get("name", "")
        chain = f'{col_type}.make("{name}")'
        if (column.get("config") or {}).get("sortable"):
            chain += ".sortable()"
        if (column.get("config") or {}).get("searchable"):
            chain += ".searchable()"
        lines.append(f"            {chain},")
    lines += ["        ])", "        return table", ""]
    return "\n".join(lines)
