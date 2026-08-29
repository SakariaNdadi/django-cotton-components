from __future__ import annotations

from typing import Any

from django.apps import AppConfig
from django.core.checks import CheckMessage, Error, Warning, register


class DjangoCottonComponentsConfig(AppConfig):
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
