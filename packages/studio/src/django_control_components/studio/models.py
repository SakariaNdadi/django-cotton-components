from __future__ import annotations

from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from .deserialize import validate_spec, validate_widgets_spec


class Visibility(models.TextChoices):
    PUBLIC = "public", "Everyone, including signed-out visitors"
    AUTHENTICATED = "auth", "Any signed-in user"
    RESTRICTED = "restricted", "Only the groups / users / permission below"


class AccessControlled(models.Model):
    """Mixin: a row's audience, resolved by an explicit grant, never by a deny.

    ``is_visible_to``: superuser → yes; then by ``visibility`` —
    ``PUBLIC`` → yes (anonymous included); ``AUTHENTICATED`` → any signed-in
    user; ``RESTRICTED`` → ``required_permission`` deny gate, then the ``users``
    / ``groups`` grants. An ungranted ``RESTRICTED`` row is invisible.

    This controls **visibility only** — a nav item pointing at a resource the
    user lacks ``view_`` permission for is still dropped by the nav builder and
    still 403s if hit directly.
    """

    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.RESTRICTED
    )
    groups = models.ManyToManyField(
        "auth.Group", blank=True, related_name="+", verbose_name="visible to groups"
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="+", verbose_name="visible to users"
    )
    required_permission = models.CharField(
        max_length=100, blank=True, help_text='e.g. "blog.view_article"'
    )

    class Meta:
        abstract = True

    def is_visible_to(self, user: Any) -> bool:
        if self.visibility == Visibility.PUBLIC:
            return True
        if user is None or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.visibility == Visibility.AUTHENTICATED:
            return True
        if self.required_permission and not user.has_perm(self.required_permission):
            return False
        if self.users.filter(pk=user.pk).exists():
            return True
        return self.groups.filter(pk__in=user.groups.all()).exists()


def visible_queryset(queryset: models.QuerySet[Any], user: Any) -> models.QuerySet[Any]:
    """The ``AccessControlled`` rows in ``queryset`` visible to ``user`` — one
    query, for nav rendering."""
    public = Q(visibility=Visibility.PUBLIC)
    if user is None or not user.is_authenticated:
        return queryset.filter(public).distinct()
    if user.is_superuser:
        return queryset
    grant = (
        public
        | Q(visibility=Visibility.AUTHENTICATED)
        | Q(users=user)
        | Q(groups__in=user.groups.all())
    )
    # required_permission is a string check we cannot express in SQL — rows that
    # carry one are filtered in Python by the caller when it matters. For nav the
    # extra rows are still gated by is_visible_to() before display.
    return queryset.filter(grant).distinct()


class DashboardSpec(AccessControlled):
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
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "dcc_studio"
        verbose_name = "dashboard spec"
        permissions = (("use_studio", "Can use the studio builder"),)

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


class PanelDashboard(AccessControlled):
    """A dashboard page defined by stored configuration instead of a
    :class:`~django_control_components.panels.DashboardPage` subclass.

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
    is_default = models.BooleanField(
        default=False, help_text="A fallback home dashboard when a user has no other."
    )
    default_for_groups = models.ManyToManyField(
        "auth.Group", blank=True, related_name="+", verbose_name="default home for groups"
    )
    revision = models.PositiveIntegerField(default=0)
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


class NavItem(AccessControlled):
    """One entry in a panel's sidebar, built in the studio instead of in code.

    A tree at most two levels deep (a group, its items, and one nesting level).
    ``target_kind`` picks how ``target`` is resolved into a URL at render time.
    """

    class Kind(models.TextChoices):
        GROUP = "group", "Group heading"
        RESOURCE = "resource", "Code resource"
        SPEC = "spec", "Studio resource"
        DASHBOARD = "dashboard", "Studio dashboard"
        URL_NAME = "url_name", "Named URL"
        URL = "url", "URL / path"

    panel = models.CharField(max_length=100, db_index=True, help_text="Panel.name")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=60, blank=True)
    order = models.IntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    target_kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.URL)
    target = models.CharField(max_length=300, blank=True)
    open_in_new_tab = models.BooleanField(default=False)

    class Meta:
        app_label = "dcc_studio"
        verbose_name = "navigation item"
        ordering = ("order", "pk")

    def __str__(self) -> str:
        return self.label

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        depth = 0
        seen: set[int] = set()
        node = self.parent
        while node is not None:
            if node.pk == self.pk or node.pk in seen:
                raise ValidationError({"parent": "A nav item cannot be its own ancestor."})
            seen.add(node.pk)
            depth += 1
            if depth > 2:
                raise ValidationError({"parent": "Navigation nests at most two levels deep."})
            node = node.parent

        if self.target_kind == self.Kind.URL and self.target:
            lowered = self.target.strip().lower()
            allowed = self.target.startswith("/") or lowered.startswith(("http://", "https://"))
            if not allowed:
                raise ValidationError(
                    {"target": "A URL target must be a site-relative path or an http(s) URL."}
                )


class NavDocument(models.Model):
    """Optimistic-concurrency token for a panel's whole sidebar.

    The sidebar is a set of :class:`NavItem` rows, not a single row, so the
    ``revision`` counter that guards :class:`DashboardSpec` lives here instead.
    Bumped once per successful nav save; a stale client revision is a 409.
    """

    panel = models.CharField(max_length=100, unique=True, help_text="Panel.name")
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "dcc_studio"
        verbose_name = "navigation document"

    def __str__(self) -> str:
        return f"{self.panel} @ r{self.revision}"


class UserPreference(models.Model):
    """Per-user studio preferences — the home dashboard override and shell state."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dcc_preference"
    )
    home_kind = models.CharField(max_length=20, blank=True)
    home_target = models.CharField(max_length=300, blank=True)
    sidebar_collapsed = models.BooleanField(default=False)
    theme = models.CharField(
        max_length=10,
        choices=(("auto", "Auto"), ("light", "Light"), ("dark", "Dark")),
        default="auto",
    )

    class Meta:
        app_label = "dcc_studio"

    def __str__(self) -> str:
        return f"preferences for {self.user}"


class SpecRevision(models.Model):
    """An immutable snapshot of a spec / dashboard document, written on every
    studio save so an edit can be rolled back."""

    dashboard_spec = models.ForeignKey(
        DashboardSpec, null=True, blank=True, on_delete=models.CASCADE, related_name="revisions"
    )
    panel_dashboard = models.ForeignKey(
        PanelDashboard, null=True, blank=True, on_delete=models.CASCADE, related_name="revisions"
    )
    payload = models.JSONField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "dcc_studio"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"revision {self.pk} @ {self.created_at:%Y-%m-%d %H:%M}"


class StudioEntry(DashboardSpec):
    """Proxy of :class:`DashboardSpec` that exists only to place a "Studio" entry
    in the Django admin index (its ``ModelAdmin`` redirects to the studio hub).
    No table, no data of its own."""

    class Meta:
        proxy = True
        app_label = "dcc_studio"
        verbose_name = "studio"
        verbose_name_plural = "studio"
        default_permissions = ()  # the entry is a redirect, not a CRUD surface
