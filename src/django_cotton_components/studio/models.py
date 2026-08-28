from __future__ import annotations

from typing import Any

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from .deserialize import validate_spec, validate_widgets_spec


class DashboardSpec(models.Model):
    """A resource defined by stored configuration instead of a Python subclass.

    ``model`` is a ``app_label.ModelName`` string resolved at request time; the
    JSON columns describe the list table, the create/edit schema and the view
    infolist. No callables, no import paths — see :mod:`.deserialize`.
    """

    slug = models.SlugField(unique=True, max_length=100)
    label = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, help_text="app_label.ModelName")

    table = models.JSONField(default=dict, blank=True)
    schema = models.JSONField(default=dict, blank=True)
    infolist = models.JSONField(default=dict, blank=True)

    nav_group = models.CharField(max_length=60, blank=True)
    nav_icon = models.CharField(max_length=60, blank=True)
    permission_prefix = models.CharField(max_length=100, blank=True)

    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "dcc_studio"
        verbose_name = "dashboard spec"

    def __str__(self) -> str:
        return self.label or self.slug

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        if not self.slug:
            self.slug = slugify(self.label or self.model.replace(".", "-"))
        model = self.resolve_model()
        try:
            validate_spec(
                {"table": self.table, "schema": self.schema, "infolist": self.infolist},
                model=model,
            )
        except ValidationError as exc:
            raise ValidationError({"table": exc.messages}) from None

    def resolve_model(self) -> type[models.Model]:
        try:
            app_label, model_name = self.model.split(".")
            return apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as exc:
            msg = f"Cannot resolve model {self.model!r}: {exc}"
            raise ValidationError({"model": msg}) from None


class PanelDashboard(models.Model):
    """A dashboard page defined by stored configuration instead of a
    :class:`~django_cotton_components.panels.DashboardPage` subclass.

    ``widgets`` is a list of ``{"type", "name"?, "config"?}`` nodes naming a
    registered ``WIDGET_TYPES`` entry. A widget's ``.query({...})`` may only
    aggregate a model listed in ``DCC["STUDIO_MODELS"]``.
    """

    slug = models.SlugField(unique=True, max_length=100)
    label = models.CharField(max_length=100, blank=True)
    widgets = models.JSONField(default=list, blank=True)

    nav_group = models.CharField(max_length=60, blank=True)
    nav_icon = models.CharField(max_length=60, blank=True)

    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "dcc_studio"
        verbose_name = "panel dashboard"

    def __str__(self) -> str:
        return self.label or self.slug

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        if not self.slug:
            self.slug = slugify(self.label or "dashboard")
        try:
            validate_widgets_spec(self.widgets)
        except ValidationError as exc:
            raise ValidationError({"widgets": exc.messages}) from None
