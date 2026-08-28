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
        self._guards: list[Callable[[HttpRequest], bool]] = []

    def path(self, value: str) -> Self:
        self._path = value.strip("/")
        return self

    def resources(self, resources: list[type[Resource]]) -> Self:
        self._resources = list(resources)
        return self

    def auth(self, *guards: Callable[[HttpRequest], bool]) -> Self:
        self._guards.extend(guards)
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
        ]

    @property
    def urls(self) -> tuple[list[Any], str]:
        patterns: list[Any] = []
        for resource in self._resources:
            patterns.extend(self._resource_patterns(resource))
        return (patterns, self.namespace)

    def mount(self) -> URLResolver:
        return path(
            f"{self._path}/", include((self.urls[0], self.namespace), namespace=self.namespace)
        )
