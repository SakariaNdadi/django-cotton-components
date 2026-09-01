from __future__ import annotations

from typing import Any

from django.apps import AppConfig
from django.core.checks import CheckMessage, Error, register


class StudioConfig(AppConfig):
    name = "django_control_components.studio"
    label = "dcc_studio"
    verbose_name = "Django Control Components — Studio"
    default_auto_field = "django.db.models.BigAutoField"


@register()
def _check_studio(app_configs: Any, **kwargs: Any) -> list[CheckMessage]:
    from django.apps import apps

    errors: list[CheckMessage] = []
    if not apps.is_installed("django_control_components"):
        errors.append(
            Error(
                "'django_control_components' must be in INSTALLED_APPS for the studio to work.",
                hint="Add 'django_control_components' before 'django_control_components.studio'.",
                id="dcc_studio.E001",
            )
        )
    return errors
