"""Bind a :class:`Schema` to a Django ``Form`` / ``ModelForm``.

The schema contributes layout and presentation; the form owns fields,
validation and persistence. This module only checks that the two line up and
surfaces a helpful error when they do not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.exceptions import SchemaError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from django.forms import BaseForm

    from ..core.component import Component
    from .schema import Schema


def iter_fields(schema: Schema) -> Iterator[Component]:
    for component in schema.component_list:
        sub = getattr(component, "iter_fields", None)
        if sub is not None:
            yield from sub()
        else:
            yield component


def _declared_names(schema: Schema) -> set[str]:
    return {f.name for f in iter_fields(schema) if f.name}


def check_alignment(schema: Schema, form: BaseForm) -> None:
    missing = _declared_names(schema) - set(form.fields)
    if missing:
        raise SchemaError(
            f"Schema references fields not on {type(form).__name__}: {sorted(missing)}. "
            f"Available: {sorted(form.fields)}"
        )


def unmapped_fields(schema: Schema, form: BaseForm) -> list[str]:
    declared = _declared_names(schema)
    return [name for name in form.fields if name not in declared]


def image_specs(schema: Schema) -> dict[str, dict[str, Any]]:
    """Map field name -> image-processing spec for FileUpload fields."""
    specs: dict[str, dict[str, Any]] = {}
    for field in iter_fields(schema):
        getter = getattr(field, "image_spec", None)
        if getter is not None and field.name and (spec := getter()):
            specs[field.name] = spec
    return specs
