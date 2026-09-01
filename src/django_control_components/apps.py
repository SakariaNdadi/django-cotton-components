from __future__ import annotations

from typing import Any

from django.apps import AppConfig
from django.core.checks import CheckMessage, Error, Warning, register


class DjangoControlComponentsConfig(AppConfig):
    name = "django_control_components"
    verbose_name = "Django Control Components"
    default_auto_field = "django.db.models.BigAutoField"


@register()
def _check_dependencies(app_configs: Any, **kwargs: Any) -> list[CheckMessage]:
    from django.apps import apps
    from django.conf import settings

    errors: list[CheckMessage] = []

    if not apps.is_installed("django_cotton"):
        errors.append(
            Error(
                "django_cotton is not in INSTALLED_APPS.",
                hint="Add 'django_cotton' to INSTALLED_APPS before 'django_control_components'.",
                id="django_control_components.E001",
            )
        )

    engines = getattr(settings, "TEMPLATES", [])
    has_django_backend = any(
        e.get("BACKEND") == "django.template.backends.django.DjangoTemplates" for e in engines
    )
    if not has_django_backend:
        errors.append(
            Warning(
                "No DjangoTemplates backend configured; component rendering will fail.",
                id="django_control_components.W002",
            )
        )

    return errors


@register()
def _check_settings(app_configs: Any, **kwargs: Any) -> list[CheckMessage]:
    """Validate the ``DCC`` dict at startup instead of on first (mistyped) access."""
    from django.apps import apps
    from django.conf import settings
    from django.utils.module_loading import import_string

    from .conf import DEFAULTS

    errors: list[CheckMessage] = []
    user_dcc = getattr(settings, "DCC", {}) or {}

    unknown = sorted(set(user_dcc) - set(DEFAULTS))
    if unknown:
        errors.append(
            Error(
                f"Unknown DCC settings key(s): {unknown}.",
                hint=f"Valid keys: {sorted(DEFAULTS)}",
                id="django_control_components.E010",
            )
        )

    icon_set = user_dcc.get("ICON_SET", DEFAULTS["ICON_SET"])
    try:
        import_string(icon_set)
    except ImportError as exc:
        errors.append(
            Error(
                f"DCC['ICON_SET'] = {icon_set!r} cannot be imported: {exc}",
                id="django_control_components.E011",
            )
        )

    for key in ("STUDIO_MODELS", "STUDIO_RESOURCE_MODELS"):
        labels = user_dcc.get(key)
        if not labels:
            continue
        for label in labels:
            try:
                apps.get_model(label)
            except (ValueError, LookupError):
                errors.append(
                    Warning(
                        f"DCC[{key!r}] names {label!r}, which does not resolve to a model.",
                        id="django_control_components.W011",
                    )
                )

    for alias, path in (user_dcc.get("STUDIO_CALLABLES") or {}).items():
        try:
            import_string(path)
        except ImportError as exc:
            errors.append(
                Warning(
                    f"DCC['STUDIO_CALLABLES'][{alias!r}] = {path!r} cannot be imported: {exc}",
                    id="django_control_components.W012",
                )
            )

    return errors
