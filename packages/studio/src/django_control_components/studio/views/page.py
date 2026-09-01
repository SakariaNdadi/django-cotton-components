"""The page builder: list / create pages, edit a page's block tree, a
revision-guarded save with 409 recovery, and a live preview.

The rich tree-editing UI lands in Phase 5 (``dccTree`` on ``x-recurse``); this
phase ships the server views and a raw-tree editor on top of the same
``dccStudioDoc`` store the dashboard and resource builders use.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import escape

from ..deserialize import build_block_tree_from_spec, validate_block_tree
from ..models import Page, SpecRevision
from ..palette import palette
from ..specmigrations import current_version
from .base import StudioView

_MOUNTS = [{"value": m.value, "label": m.label} for m in Page.Mount]


class PageIndex(StudioView):
    template_name = "django_control_components/studio/page_index.html"
    active_section = "pages"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(
            request,
            self.template_name,
            self.shell_context(pages=list(Page.objects.all()), mounts=_MOUNTS),
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        title = (request.POST.get("title") or "").strip()
        route = (request.POST.get("route") or "").strip().strip("/")
        mount = request.POST.get("mount") or Page.Mount.PANEL
        panel = (request.POST.get("panel") or "").strip()
        error = None
        if not title:
            error = "A title is required."
        elif Page.objects.filter(mount=mount, panel=panel, route=route).exists():
            error = f"A page already exists at {mount}:{panel}/{route!r}."
        if error:
            return render(
                request,
                self.template_name,
                self.shell_context(pages=list(Page.objects.all()), mounts=_MOUNTS, error=error),
            )
        page = Page(title=title, route=route, mount=mount, panel=panel, tree={})
        page.save()
        return redirect("dcc_studio:page", pk=page.pk)


class PageBuilder(StudioView):
    template_name = "django_control_components/studio/page_builder.html"
    active_section = "pages"

    def get(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> HttpResponse:
        from django.middleware.csrf import get_token

        page = _get_page(pk)
        pal = palette(request)
        boot: dict[str, Any] = {
            "doc": {"root": page.tree or {}},
            "palette": pal,
            "revision": page.revision,
            "saveUrl": reverse("dcc_studio:page-save", args=[pk]),
            "previewUrl": reverse("dcc_studio:page-preview", args=[pk]),
            "csrfToken": get_token(request),
        }
        return render(
            request,
            self.template_name,
            self.shell_context(boot_json=json.dumps(boot), page=page, block_types=pal["blocks"]),
        )


class PageSave(StudioView):
    def post(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> HttpResponse:
        page = _get_page(pk)
        doc = self.read_doc()
        try:
            client_revision = int(request.POST.get("revision", -1))
        except (TypeError, ValueError):
            client_revision = -1
        if client_revision != page.revision:
            return JsonResponse(
                {"revision": page.revision, "doc": {"root": page.tree or {}}}, status=409
            )

        root = doc.get("root") or {}
        envelope = {"schema_version": current_version(), "root": root}
        try:
            validate_block_tree(envelope, request=request)
        except ValidationError as exc:
            return JsonResponse(
                {"errors": [{"path": "", "message": str(m)} for m in exc.messages]}, status=422
            )

        page.tree = root
        page.schema_version = current_version()
        page.revision += 1
        page.save()
        SpecRevision.objects.create(
            page=page,
            payload={"tree": root, "schema_version": page.schema_version},
            author=request.user if request.user.is_authenticated else None,
        )
        _trim_revisions(page)
        return JsonResponse({"revision": page.revision})


class PagePreview(StudioView):
    def post(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> HttpResponse:
        _get_page(pk)
        doc = self.read_doc()
        envelope = {"schema_version": current_version(), "root": doc.get("root") or {}}
        try:
            block = build_block_tree_from_spec(envelope, request=request)
            from ...core.context import RenderContext

            body = str(block.render(RenderContext(request=request))) if block is not None else ""
        except ValidationError as exc:
            message = escape("; ".join(str(m) for m in exc.messages))
            body = f'<p class="dcc-studio__error">{message}</p>'
        return HttpResponse(f'<div class="dcc-page-preview">{body}</div>')


# -- helpers -------------------------------------------------------------


def _get_page(pk: int) -> Page:
    try:
        return Page.objects.get(pk=pk)
    except Page.DoesNotExist:
        raise Http404("no such page") from None


def _trim_revisions(page: Page, keep: int = 20) -> None:
    stale = page.revisions.order_by("-created_at")[keep:].values_list("pk", flat=True)
    if stale:
        SpecRevision.objects.filter(pk__in=list(stale)).delete()
