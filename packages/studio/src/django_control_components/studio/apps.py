from __future__ import annotations

from typing import Any

from django.apps import AppConfig
from django.core.checks import CheckMessage, Error, Warning, register


class StudioConfig(AppConfig):
    name = "django_control_components.studio"
    label = "dcc_studio"
    verbose_name = "Django Control Components - Studio"
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

    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured
    from django.urls import NoReverseMatch, reverse

    from ..conf import dcc_settings

    if dcc_settings.STUDIO_ADMIN_ENTRY and getattr(settings, "ROOT_URLCONF", None):
        try:
            reverse("dcc_studio:home")
        except NoReverseMatch:
            errors.append(
                Warning(
                    "The studio URLs are not mounted, but DCC['STUDIO_ADMIN_ENTRY'] is on.",
                    hint=(
                        'Add path("studio/", '
                        'include("django_control_components.studio.urls")) to your root urlconf, '
                        "or set DCC['STUDIO_ADMIN_ENTRY'] = False."
                    ),
                    id="dcc_studio.W002",
                )
            )
        except ImproperlyConfigured:  # urlconf not loadable at check time
            pass

    return errors
