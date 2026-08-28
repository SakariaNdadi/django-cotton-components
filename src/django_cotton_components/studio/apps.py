from __future__ import annotations

from django.apps import AppConfig


class StudioConfig(AppConfig):
    name = "django_cotton_components.studio"
    label = "dcc_studio"
    verbose_name = "Django Cotton Components — Studio"
    default_auto_field = "django.db.models.BigAutoField"
