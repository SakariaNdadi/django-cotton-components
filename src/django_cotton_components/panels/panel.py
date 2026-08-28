from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from django.core.exceptions import PermissionDenied
from django.urls import include, path

from . import pages
from .resource import Resource

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest
    from django.urls import URLResolver


class Panel:
    """A mount point for a set of resources.

    ``path("app/", include(Panel("admin").path("app").resources([...]).urls))``
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._path = name
        self._resources: list[type[Resource]] = []
        self._pages: list[type[Any]] = []
        self._guards: list[Callable[[HttpRequest], bool]] = []
        self._dynamic = False

    def path(self, value: str) -> Self:
        self._path = value.strip("/")
        return self

    def resources(self, resources: list[type[Resource]]) -> Self:
        self._resources = list(resources)
        return self

    def pages(self, pages: list[type[Any]]) -> Self:
        """Mount non-resource pages (a :class:`~.pages.DashboardPage`, custom
        pages). The first page with ``slug == ""`` becomes the panel index."""
        self._pages = list(pages)
        return self

    def auth(self, *guards: Callable[[HttpRequest], bool]) -> Self:
        self._guards.extend(guards)
        return self

    def dynamic(self, value: bool = True) -> Self:
        """Also serve resources defined by stored ``DashboardSpec`` rows under
        ``{panel}/d/<slug>/``. Requires ``django_cotton_components.studio`` in
        INSTALLED_APPS."""
        self._dynamic = value
        return self

    @property
    def namespace(self) -> str:
        return f"dcc-panel-{self.name}"

    def check_access(self, request: HttpRequest) -> None:
        for guard in self._guards:
            if not guard(request):
                raise PermissionDenied

    def navigation(self, request: HttpRequest) -> list[dict[str, Any]]:
        from django.urls import reverse

        items = []
        for resource in self._resources:
            if not resource.can(request, "view"):
                continue
            items.append(
                {
                    "label": resource.label(),
                    "icon": resource.navigation_icon,
                    "group": resource.navigation_group,
                    "url": reverse(f"{self.namespace}:{resource.slug()}-list"),
                }
            )
        for page in self._pages:
            if not page.nav_label:
                continue
            name = "index" if not page.slug else f"page-{page.slug}"
            items.insert(
                0 if not page.slug else len(items),
                {
                    "label": page.nav_label,
                    "icon": page.nav_icon,
                    "group": page.nav_group,
                    "url": reverse(f"{self.namespace}:{name}"),
                },
            )
        if self._dynamic:
            from ..studio.models import DashboardSpec
            from ..studio.resource import DynamicResource

            for spec in DashboardSpec.objects.filter(is_enabled=True):
                resource = DynamicResource.for_spec(spec)
                if not resource.can(request, "view"):
                    continue
                items.append(
                    {
                        "label": resource.label(),
                        "icon": spec.nav_icon,
                        "group": spec.nav_group,
                        "url": reverse(
                            f"{self.namespace}:studio-list", kwargs={"spec_slug": spec.slug}
                        ),
                    }
                )
        return items

    def _bind(self, base: type[Any], resource: type[Resource], suffix: str) -> Any:
        view_cls = type(
            f"{resource.__name__}{suffix}", (base,), {"panel": self, "resource": resource}
        )
        return view_cls.as_view()  # type: ignore[attr-defined]

    def _resource_patterns(self, resource: type[Resource]) -> list[Any]:
        slug = resource.slug()
        return [
            path(f"{slug}/", self._bind(pages.ListRecords, resource, "List"), name=f"{slug}-list"),
            path(
                f"{slug}/new/",
                self._bind(pages.CreateRecord, resource, "Create"),
                name=f"{slug}-create",
            ),
            path(
                f"{slug}/<int:pk>/",
                self._bind(pages.ViewRecord, resource, "View"),
                name=f"{slug}-view",
            ),
            path(
                f"{slug}/<int:pk>/edit/",
                self._bind(pages.EditRecord, resource, "Edit"),
                name=f"{slug}-edit",
            ),
            path(
                f"{slug}/<int:pk>/delete/",
                self._bind(pages.DeleteRecord, resource, "Delete"),
                name=f"{slug}-delete",
            ),
        ]

    def _dynamic_patterns(self) -> list[Any]:
        from ..studio import pages as spages

        def make(base: type[Any], suffix: str) -> Any:
            view_cls = type(f"Dynamic{suffix}", (base,), {"panel": self})
            return view_cls.as_view()  # type: ignore[attr-defined]

        return [
            path("d/<slug:spec_slug>/", make(spages.DynamicList, "List"), name="studio-list"),
            path(
                "d/<slug:spec_slug>/new/",
                make(spages.DynamicCreate, "Create"),
                name="studio-create",
            ),
            path(
                "d/<slug:spec_slug>/<int:pk>/",
                make(spages.DynamicView, "View"),
                name="studio-view",
            ),
            path(
                "d/<slug:spec_slug>/<int:pk>/edit/",
                make(spages.DynamicEdit, "Edit"),
                name="studio-edit",
            ),
            path(
                "d/<slug:spec_slug>/<int:pk>/delete/",
                make(spages.DynamicDelete, "Delete"),
                name="studio-delete",
            ),
        ]

    def _page_patterns(self) -> list[Any]:
        out = []
        for page in self._pages:
            bound = type(f"{page.__name__}Bound", (page,), {"panel": self})
            view = bound.as_view()  # type: ignore[attr-defined]
            if page.slug:
                out.append(path(f"{page.slug}/", view, name=f"page-{page.slug}"))
            else:
                out.append(path("", view, name="index"))
        return out

    @property
    def urls(self) -> tuple[list[Any], str]:
        patterns: list[Any] = []
        patterns.extend(self._page_patterns())
        for resource in self._resources:
            patterns.extend(self._resource_patterns(resource))
        if self._dynamic:
            patterns.extend(self._dynamic_patterns())
        return (patterns, self.namespace)

    def mount(self) -> URLResolver:
        return path(
            f"{self._path}/", include((self.urls[0], self.namespace), namespace=self.namespace)
        )
