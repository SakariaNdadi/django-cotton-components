"""Model and field discovery for the studio's dropdowns and validation.

Two audiences:

* the **picker** — which models may a staff user build a resource / dashboard
  for (``installed_models``), and what are a model's fields (``describe_model``);
* the **validator** — the set of ORM paths a stored spec is allowed to name
  (``safe_paths``), so a column/filter/sort/group-by can never reach
  ``author__user__password``.

Both honour a built-in deny list and ``DCC["STUDIO_RESOURCE_MODELS"]``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.contrib.auth import get_user_model

from ..conf import dcc_settings

if TYPE_CHECKING:
    from django.db.models import Model
    from django.http import HttpRequest

#: never offered in the picker, never a valid spec model
SENSITIVE_MODELS: frozenset[str] = frozenset(
    {
        "admin.logentry",
        "auth.permission",
        "auth.group",
        "contenttypes.contenttype",
        "sessions.session",
    }
)

#: never scaffolded, never a valid spec path — even on an otherwise-allowed model
SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        "password",
        "is_superuser",
        "is_staff",
        "user_permissions",
        "groups",
        "last_login",
    }
)

#: Django field class name -> (column type, field/input type, entry type)
DJANGO_FIELD_MAP: dict[str, tuple[str, str, str]] = {
    "BooleanField": ("BooleanColumn", "Toggle", "BooleanEntry"),
    "NullBooleanField": ("BooleanColumn", "Toggle", "BooleanEntry"),
    "DateField": ("DateColumn", "TextInput", "DateEntry"),
    "DateTimeField": ("DateColumn", "TextInput", "DateEntry"),
    "TimeField": ("TextColumn", "TextInput", "TextEntry"),
    "ImageField": ("ImageColumn", "FileUpload", "TextEntry"),
    "FileField": ("TextColumn", "FileUpload", "TextEntry"),
    "EmailField": ("TextColumn", "EmailInput", "TextEntry"),
    "TextField": ("TextColumn", "Textarea", "TextEntry"),
    "IntegerField": ("TextColumn", "TextInput", "TextEntry"),
    "BigIntegerField": ("TextColumn", "TextInput", "TextEntry"),
    "PositiveIntegerField": ("TextColumn", "TextInput", "TextEntry"),
    "FloatField": ("TextColumn", "TextInput", "TextEntry"),
    "DecimalField": ("TextColumn", "TextInput", "TextEntry"),
    "ForeignKey": ("TextColumn", "Select", "TextEntry"),
    "OneToOneField": ("TextColumn", "Select", "TextEntry"),
}
_DEFAULT_TYPES = ("TextColumn", "TextInput", "TextEntry")
_SEARCHABLE_KINDS = frozenset({"CharField", "TextField", "EmailField", "SlugField"})


def _label_of(model: type[Model]) -> str:
    return f"{model._meta.app_label}.{model._meta.model_name}"


def is_sensitive_model(model: type[Model]) -> bool:
    label = _label_of(model).lower()
    if label in SENSITIVE_MODELS:
        return True
    return model._meta.app_label == "dcc_studio"


def _user_can_view(request: HttpRequest | None, model: type[Model]) -> bool:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.has_perm(f"{model._meta.app_label}.view_{model._meta.model_name}")


def _picker_allows(model: type[Model]) -> bool:
    allow = dcc_settings.STUDIO_RESOURCE_MODELS
    if allow is None:
        return True
    return _label_of(model) in set(allow)


def installed_models(request: HttpRequest | None, *, trusted: bool = False) -> list[dict[str, str]]:
    """Models a staff user may build a resource / dashboard for.

    ``trusted=True`` is for the management command: it runs from a shell with DB
    access, so the per-user ``view_`` permission gate (and the user-model
    superuser restriction) do not apply — only the sensitive-model deny list and
    ``DCC["STUDIO_RESOURCE_MODELS"]`` still filter.
    """
    user = getattr(request, "user", None)
    is_superuser = bool(user and getattr(user, "is_superuser", False))
    user_model = get_user_model()
    out: list[dict[str, str]] = []
    for model in apps.get_models():
        if is_sensitive_model(model):
            continue
        if model is user_model and not is_superuser and not trusted:
            continue
        if not _picker_allows(model):
            continue
        if not trusted and not _user_can_view(request, model):
            continue
        out.append(
            {
                "label": _label_of(model),
                "verbose_name": str(model._meta.verbose_name_plural).title(),
                "app_label": model._meta.app_label,
            }
        )
    return sorted(out, key=lambda row: row["label"])


def resolve_model(label: str) -> type[Model]:
    return apps.get_model(label)


def _suggest_types(field: Any) -> tuple[str, str, str]:
    if getattr(field, "choices", None):
        return ("BadgeColumn", "Select", "BadgeEntry")
    return DJANGO_FIELD_MAP.get(type(field).__name__, _DEFAULT_TYPES)


def describe_model(model: type[Model], request: HttpRequest | None = None) -> list[dict[str, Any]]:
    """Field descriptors for the builder's field pickers."""
    rows: list[dict[str, Any]] = []
    for field in model._meta.get_fields():
        name = field.name
        if name in SENSITIVE_FIELDS:
            continue
        if not getattr(field, "concrete", False):
            continue  # reverse relations, generic relations
        is_relation = bool(getattr(field, "is_relation", False))
        if is_relation and not (field.many_to_one or field.one_to_one):
            continue  # m2m: not a scalar cell
        column, field_input, entry = _suggest_types(field)
        rows.append(
            {
                "name": name,
                "verbose_name": str(getattr(field, "verbose_name", name)).title(),
                "kind": type(field).__name__,
                "is_relation": is_relation,
                "column_type": column,
                "field_type": field_input,
                "entry_type": entry,
                "sortable": True,
                "searchable": type(field).__name__ in _SEARCHABLE_KINDS,
                "choices": [list(pair) for pair in (getattr(field, "choices", None) or [])],
            }
        )
    return rows


def safe_paths(
    model: type[Model], request: HttpRequest | None = None, *, depth: int = 1
) -> frozenset[str]:
    """ORM paths (``__`` notation) a spec over ``model`` may name.

    Own concrete fields plus, one relation deep, ``fk__field`` for forward
    FK/O2O to a non-sensitive related model. ``pk`` is always allowed.
    """
    paths: set[str] = {"pk"}
    for field in model._meta.get_fields():
        if field.name in SENSITIVE_FIELDS or not getattr(field, "concrete", False):
            continue
        paths.add(field.name)
        if depth > 0 and (field.many_to_one or field.one_to_one):
            related = field.related_model
            if related is None or is_sensitive_model(related):
                continue
            for sub in related._meta.get_fields():
                if sub.name in SENSITIVE_FIELDS or not getattr(sub, "concrete", False):
                    continue
                if getattr(sub, "is_relation", False):
                    continue
                paths.add(f"{field.name}__{sub.name}")
    return frozenset(paths)


def normalize_path(path: str) -> str:
    """Column dot notation (``author.name``) -> ORM notation (``author__name``)."""
    return path.replace(".", "__")
